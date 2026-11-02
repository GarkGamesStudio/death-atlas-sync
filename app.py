"""Compact setup and Windows tray. GUI callbacks never perform network requests."""
import argparse, ctypes, json, os, queue, sys, threading, time, webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import engine
import updates
from branding import apply_window_icon, tray_image
from localization import tr, font_family
SOURCE_URL = 'https://github.com/GarkGamesStudio/death-atlas-sync'
PRIVACY_URL = 'https://garkgames.com/death-atlas/privacy/'

def tray_labels():
    return (tr('configure'), tr('about'), tr('close'))

class App:

    def __init__(self, root, store, service, background=False, state=None):
        self.root = root
        self.store = store
        self.service = service
        self.state = store.read() if state is None else state
        self.messages = queue.Queue()
        self.wake = threading.Event()
        self.paused = threading.Event()
        self.paused.set()
        self.quit = threading.Event()
        self.operation = threading.Lock()
        self.tray_ready = threading.Event()
        self.icon = None
        self.busy = False
        self.scanning = False
        self.scan_generation = 0
        self.candidates = []
        self.last_error = ''
        self.last_status = tr('last_initial')
        self.window_icon = apply_window_icon(root)
        root.title('Death Atlas Sync')
        root.minsize(540, 290)
        root.resizable(True, False)
        root.configure(bg='#111a20')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#111a20')
        style.configure('TLabel', background='#111a20', foreground='#d8e3d7')
        style.configure('TButton', padding=(10, 6))
        style.configure('.', font=(font_family(), 10))
        style.configure('TCheckbutton', background='#111a20', foreground='#d8e3d7')
        self.panel = ttk.Frame(root, padding=18)
        self.panel.pack(fill='both', expand=True)
        ttk.Label(self.panel, text=tr('folder'), font=(font_family(), 13, 'bold')).pack(anchor='w', pady=(0, 8))
        self.folder = tk.StringVar()
        self.entry = ttk.Entry(self.panel, textvariable=self.folder)
        self.entry.pack(fill='x')
        actions = ttk.Frame(self.panel)
        actions.pack(fill='x', pady=8)
        self.detect_button = ttk.Button(actions, text=tr('detect'), command=self.rescan)
        self.detect_button.pack(side='left')
        self.choose_button = ttk.Button(actions, text=tr('choose'), command=self.choose)
        self.choose_button.pack(side='left', padx=6)
        self.ok_button = ttk.Button(actions, text=tr('ok'), command=self.start)
        self.ok_button.pack(side='right')
        self.autostart = tk.BooleanVar(value=bool(self.state.get('startup', False)))
        self.startup_checkbox = ttk.Checkbutton(self.panel, text=tr('autostart'), variable=self.autostart)
        self.startup_checkbox.pack(anchor='w', pady=(0, 8))
        if os.name != 'nt':
            self.autostart.set(False)
            self.startup_checkbox.pack_forget()
        self.account_row = ttk.Frame(self.panel)
        ttk.Label(self.account_row, text=tr('account')).pack(anchor='w')
        self.selection = tk.StringVar()
        self.combo = ttk.Combobox(self.account_row, textvariable=self.selection, state='readonly')
        self.combo.pack(fill='x', pady=(3, 8))
        self.combo.bind('<<ComboboxSelected>>', lambda event: self.selected_folder())
        self.notice = ttk.Label(self.panel, text=tr('notice'), wraplength=500, foreground='#aab9bc')
        self.notice.pack(anchor='w', pady=(5, 0))
        link = ttk.Label(self.panel, text=tr('privacy'), foreground='#cbf276', cursor='hand2')
        link.pack(anchor='w', pady=(3, 8))
        link.bind('<Button-1>', lambda event: webbrowser.open(PRIVACY_URL))
        self.status = tk.StringVar(value=tr('initial'))
        ttk.Label(self.panel, textvariable=self.status, wraplength=500).pack(anchor='w')
        if os.name != 'nt':
            ttk.Label(self.panel, text=tr('platform_preview'), wraplength=500, foreground='#cbf276').pack(anchor='w', pady=(8, 0))
            desktop_actions=ttk.Frame(self.panel);desktop_actions.pack(fill='x',pady=(8,0))
            ttk.Button(desktop_actions,text=tr('about'),command=self.about).pack(side='left')
            ttk.Button(desktop_actions,text=tr('close'),command=self.close).pack(side='right')
            if sys.platform.startswith('linux'):
                from linux_desktop import show_help
                ttk.Button(desktop_actions,text=tr('linux_help'),command=lambda:show_help(root)).pack(side='left',padx=6)
        profile = self.state.get('selected')
        if profile and (Path(profile['addon']) / 'DeathAtlas.toc').is_file():
            self.set_candidates([profile], profile)
        else:
            self.rescan()
        self.tray()
        root.protocol('WM_DELETE_WINDOW', self.window_close)
        self.fit_window()
        self.poll_id = root.after(100, self.poll)
        threading.Thread(target=self.loop, daemon=True).start()
        if background and profile in self.candidates and self.state.get('enabled') and engine.consented(self.state) and self.icon:

            def resume_background():
                if self.tray_ready.wait(5) and self.icon:
                    self.messages.put(('resume_background',))
                else:
                    self.messages.put(('setup_error', tr('tray_failed')))
            threading.Thread(target=resume_background, daemon=True).start()

    def fit_window(self):
        self.root.update_idletasks()
        self.root.geometry(str(max(540, self.panel.winfo_reqwidth())) + 'x' + str(max(290, self.panel.winfo_reqheight())))

    def set_busy(self, value):
        self.busy = value
        for widget in (self.entry, self.detect_button, self.choose_button, self.ok_button, self.startup_checkbox):
            widget.configure(state='disabled' if value else 'normal')
        self.combo.configure(state='disabled' if value else 'readonly')

    def selected_folder(self):
        index = self.combo.current()
        if 0 <= index < len(self.candidates):
            self.folder.set(str(Path(self.candidates[index]['addon']).parents[2]))

    def profile_label(self, profile):
        client = Path(profile['addon']).parents[2]
        account = Path(profile['saved']).parents[1].name if profile.get('saved') else tr('pending_account')
        return account + ' · ' + client.name + ' · ' + str(client.parent)

    def set_candidates(self, values, preferred=None):
        self.candidates = values
        self.combo['values'] = [self.profile_label(p) for p in values]
        if preferred in values:
            self.combo.current(values.index(preferred))
        elif len(values) == 1:
            self.combo.current(0)
        else:
            self.selection.set('')
        self.selected_folder()
        if hasattr(self, 'account_row'):
            if len(values) > 1:
                self.account_row.pack(fill='x', before=self.notice)
            else:
                self.account_row.pack_forget()
        if not values:
            self.status.set(tr('no_history'))
        elif self.combo.current() < 0:
            self.status.set(tr('multiple'))
        else:
            self.status.set(tr('found'))
        if hasattr(self, 'panel'):
            self.fit_window()

    def rescan(self):
        if self.busy or self.scanning:
            return
        self.scanning = True
        self.scan_generation += 1
        generation = self.scan_generation
        preferred = [self.folder.get()] if self.folder.get() else []
        current = self.candidates[self.combo.current()] if 0 <= self.combo.current() < len(self.candidates) else None
        self.status.set(tr('searching'))

        def task():
            try:
                self.messages.put(('discovered', engine.discover(preferred), current, generation))
            except Exception:
                self.messages.put(('discovery_failed', generation))
        threading.Thread(target=task, daemon=True).start()

    def choose(self):
        if self.busy:
            return
        path = filedialog.askdirectory(title=tr('folder'), parent=self.root)
        if path:
            self.scan_generation += 1
            self.scanning = False
            self.folder.set(path)
            self.set_candidates(engine.detect(path))

    def start(self):
        if self.busy:
            return
        selected = self.candidates[self.combo.current()] if 0 <= self.combo.current() < len(self.candidates) else None
        selected_root = str(Path(selected['addon']).parents[2]) if selected else ''
        if self.folder.get() and (not selected or os.path.normcase(os.path.abspath(self.folder.get())) != os.path.normcase(os.path.abspath(selected_root))):
            self.set_candidates(engine.detect(self.folder.get()))
        index = self.combo.current()
        if index < 0 or index >= len(self.candidates):
            messagebox.showerror(tr('start_failed'), tr('invalid_folder'), parent=self.root)
            return
        self.scan_generation += 1
        self.scanning = False
        self.paused.set()
        self.set_busy(True)
        self.status.set(tr('verifying'))
        profile = dict(self.candidates[index])
        startup_requested = bool(self.autostart.get())

        def task():
            try:
                if os.name == 'nt' and (not self.tray_ready.wait(5) or not self.icon):
                    raise engine.CheckError('TRAY', tr('tray_failed'))
                with self.operation:
                    if self.quit.is_set():
                        return
                    self.state.update(selected=profile, consent=True, consentPolicy=engine.POLICY, enabled=False)
                    self.store.write(self.state)
                    result = engine.sync_profile(profile, self.state, self.store, self.service, self.quit.is_set) if profile.get('saved') else {'waiting':True}
                    if self.quit.is_set():
                        return
                    try:
                        if startup_requested or bool(self.state.get('startup', False)) != startup_requested:
                            engine.startup(startup_requested)
                    except Exception:
                        raise engine.CheckError('STARTUP', tr('startup_failed')) from None
                    self.state.update(startup=startup_requested, enabled=True)
                    self.store.write(self.state)
                self.messages.put(('connected', result))
            except Exception as exc:
                self.messages.put(('setup_error', engine.describe_error(exc)))
        threading.Thread(target=task, daemon=True).start()

    def tray(self):
        if sys.platform.startswith('linux'):
            # Linux desktops disagree about tray support, especially Wayland.
            # Keep a visible, minimizable window instead of hiding a working sync.
            self.tray_ready.set()
            return
        try:
            import pystray
            image = tray_image()
            callbacks = (lambda *_: self.messages.put(('configure',)), lambda *_: self.messages.put(('about',)), lambda *_: self.messages.put(('exit',)))
            menu = pystray.Menu(*(pystray.MenuItem(label, callback, default=i == 0) for i, (label, callback) in enumerate(zip(tray_labels(), callbacks))))
            self.icon = pystray.Icon('DeathAtlasSync', image, 'Death Atlas Sync', menu)

            def ready(icon):
                icon.visible = True
                self.tray_ready.set()
            self.icon.run_detached(setup=ready)
        except Exception:
            self.icon = None
            self.tray_ready.set()

    def configure(self):
        self.root.deiconify()
        self.root.lift()
        self.fit_window()

    def about(self):
        dialog = tk.Toplevel(self.root)
        dialog.title(tr('about_title'))
        dialog.resizable(False, False)
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, image=self.window_icon).pack(anchor='w', pady=(0, 6))
        ttk.Label(frame, text='Death Atlas Sync ' + engine.VERSION, font=(font_family(), 13, 'bold')).pack(anchor='w')
        ttk.Label(frame, text=tr('about_text', status=self.last_status), wraplength=430).pack(anchor='w', pady=12)
        update=self.state.get('updates',{}).get('available')
        if update:
            ttk.Button(frame,text=tr('update_available',version=update['version']),command=lambda:webbrowser.open(updates.DOWNLOADS)).pack(fill='x',pady=(0,8))
        ttk.Button(frame, text=tr('github'), command=lambda: webbrowser.open(SOURCE_URL)).pack(fill='x')
        ttk.Button(frame, text=tr('privacy'), command=lambda: webbrowser.open(PRIVACY_URL)).pack(fill='x', pady=5)
        ttk.Button(frame, text=tr('licenses'), command=self.licenses).pack(fill='x')
        ttk.Button(frame, text=tr('erasure_button'), command=self.erase_shared_data).pack(fill='x', pady=(8, 0))
        ttk.Button(frame, text=tr('ok'), command=dialog.destroy).pack(anchor='e', pady=(10, 0))

    def erase_shared_data(self):
        if self.busy:
            return
        profile = self.state.get('selected')
        if not profile:
            messagebox.showerror(tr('erasure_button'), tr('erasure_no_key'), parent=self.root)
            return
        if not messagebox.askyesno(tr('erasure_button'), tr('erasure_confirm'), parent=self.root):
            return
        self.paused.set()
        self.set_busy(True)
        def task():
            try:
                with self.operation:
                    result = engine.request_erasure(profile, self.state, self.store, self.service)
                self.messages.put(('erasure_result', tr('erasure_'+result['erasure'])))
            except Exception as exc:
                self.messages.put(('erasure_error', engine.describe_error(exc)))
        threading.Thread(target=task, daemon=True).start()

    def licenses(self):
        base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
        files = [base / 'LICENSE.txt'] + sorted((base / 'THIRD_PARTY').rglob('*'))
        texts = []
        for path in files:
            if path.is_file() and ('LICENSE' in path.name.upper() or path.name.upper().startswith('COPYING')):
                texts.append(path.relative_to(base).as_posix() + '\n\n' + path.read_text(encoding='utf-8', errors='replace'))
        window = tk.Toplevel(self.root)
        window.title(tr('license_title'))
        window.geometry('680x440')
        from tkinter.scrolledtext import ScrolledText
        text = ScrolledText(window, wrap='word', padx=12, pady=12)
        text.pack(fill='both', expand=True)
        text.insert('1.0', '\n\n--------------------\n\n'.join(texts))
        text.configure(state='disabled')

    def window_close(self):
        if self.icon and (not self.paused.is_set()):
            self.root.withdraw()
        else:
            self.close()

    def close(self):
        self.quit.set()
        self.paused.set()
        self.wake.set()
        if getattr(self, 'poll_id', None):
            try:
                self.root.after_cancel(self.poll_id)
            except tk.TclError:
                pass
        if self.icon:
            self.icon.stop()
        self.root.destroy()

    def poll(self):
        try:
            while True:
                value = self.messages.get_nowait()
                kind = value[0]
                if kind == 'discovered' and value[3] == self.scan_generation:
                    self.scanning = False
                    self.set_candidates(value[1], value[2])
                elif kind == 'discovery_failed' and value[1] == self.scan_generation:
                    self.scanning = False
                    self.status.set(tr('search_failed'))
                elif kind == 'connected':
                    self.set_busy(False)
                    self.paused.clear()
                    self.last_error = ''
                    pending=value[1].get('waiting',False)
                    self.last_status = tr('pending_save') if pending else tr('connected', time=time.strftime('%H:%M'))
                    self.status.set(self.last_status)
                    if self.icon:
                        self.root.withdraw()
                    messagebox.showinfo('Death Atlas Sync', tr('pending_success') if pending else (tr('success') if self.icon else tr('foreground_success')), parent=self.root)
                    self.wake.set()
                elif kind == 'update_available':
                    if self.icon:
                        try:self.icon.notify(tr('update_available',version=value[1]),'Death Atlas Sync')
                        except Exception:pass
                    else:self.status.set(tr('update_available',version=value[1]))
                elif kind == 'setup_error':
                    self.set_busy(False)
                    self.last_status = value[1]
                    self.status.set(value[1])
                    self.configure()
                    messagebox.showerror(tr('start_failed'), value[1], parent=self.root)
                    self.fit_window()
                elif kind == 'status':
                    self.last_status = value[1]
                    if not self.icon:self.status.set(value[1])
                elif kind in ('erasure_result', 'erasure_error'):
                    self.set_busy(False)
                    self.last_status = value[1]
                    self.status.set(value[1])
                    show = messagebox.showinfo if kind == 'erasure_result' else messagebox.showerror
                    show(tr('erasure_button'), value[1], parent=self.root)
                elif kind == 'resume_background':
                    self.paused.clear()
                    self.wake.set()
                    self.root.withdraw()
                elif kind == 'background_error':
                    self.last_status = value[1]
                    if not self.icon:self.status.set(value[1])
                    if self.icon and value[1] != self.last_error:
                        try:
                            self.icon.notify(tr('retry_notice'), 'Death Atlas Sync')
                        except Exception:
                            pass
                    self.last_error = value[1]
                elif kind == 'configure':
                    self.configure()
                elif kind == 'about':
                    self.about()
                elif kind == 'exit':
                    self.close()
                    return
        except queue.Empty:
            pass
        self.poll_id = self.root.after(100, self.poll)

    def loop(self):
        signature = None
        while not self.quit.is_set():
            force = self.wake.wait(60)
            self.wake.clear()
            if self.quit.is_set():
                return
            if self.paused.is_set() or not self.state.get('enabled') or (not self.state.get('selected')):
                continue
            try:
                with self.operation:
                    if self.paused.is_set() or self.quit.is_set():
                        continue
                    profile = dict(self.state['selected'])
                    update,changed=updates.check(self.state,engine.VERSION)
                    if changed:
                        self.store.write(self.state)
                        if update and self.state['updates'].get('notified')!=update['version']:
                            self.messages.put(('update_available',update['version']))
                            self.state['updates']['notified']=update['version'];self.store.write(self.state)
                    if engine.data.wow_running():
                        self.messages.put(('status', tr('waiting')))
                        continue
                    resolved=engine.ready_profile(profile)
                    if resolved!=profile:
                        profile=resolved;self.state['selected']=profile;self.store.write(self.state)
                    if not profile.get('saved') or not Path(profile['saved']).is_file():
                        self.messages.put(('status',tr('pending_save')))
                        continue
                    saved = Path(profile['saved'])
                    stat = saved.stat()
                    current = (str(saved), stat.st_mtime_ns, stat.st_size, engine.refresh_slot())
                    if current != signature or force:
                        engine.sync_profile(profile, self.state, self.store, self.service, lambda: self.paused.is_set() or self.quit.is_set())
                        signature = current
                        self.messages.put(('status', tr('updated', time=time.strftime('%H:%M'))))
            except Exception as exc:
                self.messages.put(('background_error', engine.describe_error(exc)))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--background', action='store_true')
    parser.add_argument('--service', default=engine.DEFAULT_SERVICE)
    parser.add_argument('--self-test-output')
    args = parser.parse_args()
    if args.self_test_output:
        root = tk.Tk()
        root.withdraw()
        brand_icon = apply_window_icon(root)
        root.update()
        root.destroy()
        base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
        import localization
        if os.name != 'nt':
            from platform_support import tls_context
            assert tls_context().cert_store_stats()['x509_ca'] > 0
        Path(args.self_test_output).write_text(json.dumps({'version': engine.VERSION, 'tk': True, 'dpapi': engine.protect(engine.protect(b'fixture'), True) == b'fixture', 'embeddedLicense': (base / 'LICENSE.txt').is_file(), 'embeddedThirdParty': (base / 'THIRD_PARTY').is_dir(), 'language': localization.LANGUAGE, 'localeCount': len(localization.LOCALES), 'catalogKeys': len(localization.CATALOG), 'brandAssets': all((base/'assets'/name).is_file() for name in ('DeathAtlas.ico','Icon32.png','Icon64.png')), 'windowIconLoaded': True}))
        return
    mutex = None
    if os.name == 'nt':
        ctypes.windll.kernel32.CreateMutexW.restype = ctypes.c_void_p
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, 'Local\\DeathAtlasSync')
        if ctypes.windll.kernel32.GetLastError() == 183:
            messagebox.showinfo('Death Atlas Sync', tr('already_open'))
            return
    root = tk.Tk()
    instance = None
    try:
        from platform_support import settings_path,acquire_instance
        if os.name!='nt':
            instance=acquire_instance()
            if instance is None:
                messagebox.showinfo('Death Atlas Sync',tr('linux_open') if sys.platform.startswith('linux') else tr('already_open'));root.destroy();return
        path = settings_path()
        store=engine.Settings(path)
        if sys.platform.startswith('linux'):
            from linux_desktop import Setup
            Setup(root,store,lambda state:App(root,store,engine.endpoint(args.service),args.background,state=state))
        else:
            App(root, store, engine.endpoint(args.service), args.background)
        root.mainloop()
    except Exception:
        messagebox.showerror('Death Atlas Sync', tr('settings_failed'))
        root.destroy()
    finally:
        if instance:instance.close()
        if mutex:
            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(mutex))
if __name__ == '__main__':
    main()
