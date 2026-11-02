"""Responsive setup/recovery for Linux native credential storage; no network operations."""
import queue,threading
import tkinter as tk
from tkinter import ttk
from localization import tr,font_family
import linux_credentials as credentials

class Setup:
 def __init__(self,root,store=None,on_ready=None):
  self.root=root;self.store=store;self.on_ready=on_ready;self.events=queue.Queue();self.closed=False
  root.title('Death Atlas Sync · Linux');root.configure(bg='#111a20')
  style=ttk.Style(root);style.theme_use('clam')
  style.configure('TFrame',background='#111a20');style.configure('TLabel',background='#111a20',foreground='#d8e3d7')
  style.configure('TButton',padding=(10,6));style.configure('.',font=(font_family(),10))
  self.frame=ttk.Frame(root,padding=20);self.frame.pack(fill='both',expand=True)
  ttk.Label(self.frame,text=tr('linux_help'),font=(font_family(),14,'bold')).pack(anchor='w')
  ttk.Label(self.frame,text=tr('linux_explain'),wraplength=520).pack(anchor='w',pady=10)
  self.status=tk.StringVar(value=tr('linux_checking'))
  ttk.Label(self.frame,textvariable=self.status,wraplength=520).pack(anchor='w',pady=8)
  self.details=ttk.Frame(self.frame)
  if not on_ready:self.details.pack(fill='x')
  ttk.Label(self.details,text=tr('linux_instructions'),wraplength=520).pack(anchor='w',pady=10)
  distro,command=credentials.instructions()
  if command:
   ttk.Label(self.details,text=distro).pack(anchor='w')
   value=tk.StringVar(value=command)
   ttk.Entry(self.details,textvariable=value,state='readonly',width=60).pack(fill='x',pady=5)
  row=ttk.Frame(self.frame);row.pack(fill='x',pady=(12,0))
  self.row=row
  self.unlock=ttk.Button(row,text=tr('linux_unlock'),command=lambda:self.run(True));self.unlock.pack(side='left')
  self.retry=ttk.Button(row,text=tr('linux_retry'),command=self.run);self.retry.pack(side='left',padx=6)
  ttk.Button(row,text=tr('close'),command=self.close).pack(side='right')
  root.protocol('WM_DELETE_WINDOW',self.close)
  self.run();self.timer=root.after(100,self.poll)

 def run(self,unlock=False):
  self.unlock.configure(state='disabled');self.retry.configure(state='disabled');self.status.set(tr('linux_checking'))
  def task():
   try:
    credentials.check(unlock=unlock)
    state=self.store.read() if self.store else None
    self.events.put(('ready',state))
   except credentials.CredentialError as error:self.events.put(('error',error.code))
   except Exception:self.events.put(('error','config' if self.store else 'store'))
  threading.Thread(target=task,daemon=True).start()

 def poll(self):
  if self.closed:return
  try:
   kind,value=self.events.get_nowait()
   self.retry.configure(state='normal')
   if kind=='ready':
    self.status.set(tr('linux_ready'))
    if self.on_ready:
     self.closed=True;self.frame.destroy();self.on_ready(value);return
   else:
    self.details.pack(fill='x',before=self.row)
    self.status.set(tr('linux_'+value))
    self.unlock.configure(state='normal' if value=='locked' else 'disabled')
  except queue.Empty:pass
  self.timer=self.root.after(100,self.poll)

 def close(self):
  self.closed=True
  if getattr(self,'timer',None):self.root.after_cancel(self.timer)
  self.root.destroy()

def show_help(root):Setup(tk.Toplevel(root))
