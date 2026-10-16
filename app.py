from __future__ import annotations
from datetime import datetime
from pathlib import Path
import csv, queue, threading, tkinter as tk
from tkinter import filedialog, messagebox, ttk
from iec61850.backend import Backend, ModelItem
from iec61850.scl import load_scl
from iec61850.send_dialog import SendDialog
from iec61850.monitor_dialog import MonitorDialog

APP_NAME="IEC61850 Reader"; APP_VERSION="0.2.0"

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title(f"{APP_NAME} {APP_VERSION}"); self.geometry("1450x820"); self.minsize(1050,620)
        self.backend=Backend(); self.events=queue.Queue(); self.items=[]; self.connected=False
        self.host=tk.StringVar(value="192.168.2.213"); self.port=tk.StringVar(value="102"); self.status=tk.StringVar(value="Bereit")
        self.filter=tk.StringVar(); self._layout(); self.after(50,self._events)
    def _layout(self):
        top=ttk.LabelFrame(self,text="IEC 61850 / MMS",padding=8); top.pack(fill="x",padx=8,pady=8)
        for c,(label,var,width) in enumerate((("Host / IP",self.host,24),("TCP-Port",self.port,9))):
            ttk.Label(top,text=label).grid(row=0,column=c,sticky="w",padx=3); ttk.Entry(top,textvariable=var,width=width).grid(row=1,column=c,padx=3)
        self.connect_btn=ttk.Button(top,text="Verbindung prüfen",command=self.probe); self.connect_btn.grid(row=1,column=2,padx=4)
        ttk.Button(top,text="Online-Modell lesen",command=self.browse).grid(row=1,column=3,padx=4)
        ttk.Button(top,text="SCL importieren",command=self.import_scl).grid(row=1,column=4,padx=4)
        ttk.Button(top,text="Senden ...",command=self.open_send).grid(row=1,column=5,padx=4)
        ttk.Button(top,text="Reports / GOOSE / TLS ...",command=self.open_monitors).grid(row=1,column=6,padx=4)
        ttk.Label(top,text="Filter").grid(row=0,column=7,sticky="w"); ttk.Entry(top,textvariable=self.filter,width=25).grid(row=1,column=7,padx=4); self.filter.trace_add("write",lambda *_:self.render())
        split=ttk.Panedwindow(self,orient="horizontal"); split.pack(fill="both",expand=True,padx=8,pady=4)
        left=ttk.LabelFrame(split,text="Gerätemodell",padding=4); right=ttk.LabelFrame(split,text="Werte und Ereignisse",padding=4); split.add(left,weight=2); split.add(right,weight=3)
        self.tree=ttk.Treeview(left,columns=("kind",),show="tree headings"); self.tree.heading("#0",text="Objektreferenz"); self.tree.heading("kind",text="Art"); self.tree.column("kind",width=80,stretch=False); self.tree.pack(fill="both",expand=True); self.tree.bind("<Double-1>",lambda _e:self.read_selected())
        bar=ttk.Frame(right); bar.pack(fill="x"); ttk.Button(bar,text="Auswahl lesen",command=self.read_selected).pack(side="left"); ttk.Button(bar,text="CSV exportieren",command=self.export_csv).pack(side="right")
        self.values=ttk.Treeview(right,columns=("reference","fc","value","time"),show="headings")
        for name,text,width in (("reference","Objektreferenz",430),("fc","FC",60),("value","Wert",280),("time","Zeit",170)): self.values.heading(name,text=text); self.values.column(name,width=width)
        self.values.pack(fill="both",expand=True,pady=4)
        self.log=tk.Text(right,height=9,bg="#101418",fg="#d7e1e8",font=("Consolas",9)); self.log.pack(fill="x")
        ttk.Label(self,textvariable=self.status,padding=6).pack(fill="x")
    def target(self):
        host=self.host.get().strip(); port=int(self.port.get())
        if not host or not 1<=port<=65535: raise ValueError("Host beziehungsweise Port ist ungültig")
        return host,port
    def background(self,fn): threading.Thread(target=lambda:self._run(fn),daemon=True).start()
    def _run(self,fn):
        try: self.events.put(("ok",fn()))
        except Exception as e: self.events.put(("error",str(e)))
    def _events(self):
        try:
            while True:
                kind,data=self.events.get_nowait()
                if kind=="error": self.status.set(data); messagebox.showerror(APP_NAME,data,parent=self)
                elif isinstance(data,list): self.items=data; self.render(); self.status.set(f"{len(data)} Modellelemente geladen")
                else: self.status.set(str(data or "Fertig"))
        except queue.Empty: pass
        self.after(50,self._events)
    def probe(self):
        h,p=self.target(); self.status.set("Verbindung wird geprüft ..."); self.background(lambda:(self.backend.probe(h,p),"MMS-Verbindung erfolgreich")[1])
    def browse(self):
        h,p=self.target(); self.status.set("Online-Modell wird gelesen ..."); self.background(lambda:self.backend.browse(h,p))
    def import_scl(self):
        path=filedialog.askopenfilename(filetypes=[("SCL-Dateien","*.icd *.cid *.scd *.iid"),("XML","*.xml")]);
        if path: self.items=load_scl(path); self.render(); self.status.set(f"SCL importiert: {Path(path).name}")
    def render(self):
        self.tree.delete(*self.tree.get_children()); nodes={}; needle=self.filter.get().casefold().strip()
        for item in self.items:
            if needle and needle not in item.reference.casefold() and needle not in item.kind.casefold(): continue
            parent=""; parts=item.reference.replace("/",".").split("."); built=""
            for i,part in enumerate(parts):
                built=part if not built else built+"."+part
                if built not in nodes: nodes[built]=self.tree.insert(parent,"end",text=part,values=(item.kind if i==len(parts)-1 else ""),tags=(item.reference if i==len(parts)-1 else "",));
                parent=nodes[built]
    def selected_ref(self):
        sel=self.tree.selection();
        if not sel: return ""
        tags=self.tree.item(sel[0],"tags"); return tags[0] if tags else ""
    def read_selected(self):
        ref=self.selected_ref()
        if not ref: messagebox.showinfo(APP_NAME,"Bitte ein Datenattribut auswählen.",parent=self); return
        self.open_send(ref)
    def open_send(self,ref=""):
        SendDialog(self,self.do_read,self.do_write,self.do_control,ref)
    def open_monitors(self):
        MonitorDialog(self,self.backend,self.target,self._log)
    def do_read(self,ref,fc):
        h,p=self.target(); value=self.backend.read(h,p,ref,fc); now=f"{datetime.now():%Y-%m-%d %H:%M:%S}"; self.values.insert("",0,values=(ref,fc,value,now)); self._log(f"READ {ref} [{fc}] = {value}")
    def do_write(self,ref,fc,typ,value):
        h,p=self.target(); self.backend.write(h,p,ref,fc,typ,value); self._log(f"WRITE {ref} [{fc}] {typ}={value}")
    def do_control(self,ref,typ,value,action,origin,test,interlock,synchro):
        h,p=self.target(); self.backend.control(h,p,ref,typ,value,action,origin,test,interlock,synchro); self._log(f"CONTROL {action} {ref} {value}")
    def _log(self,text): self.log.insert("end",f"{datetime.now():%H:%M:%S} {text}\n"); self.log.see("end")
    def export_csv(self):
        path=filedialog.asksaveasfilename(defaultextension=".csv",filetypes=[("CSV","*.csv")]);
        if not path:return
        with open(path,"w",newline="",encoding="utf-8-sig") as f:
            w=csv.writer(f,delimiter=";"); w.writerow(("Objektreferenz","FC","Wert","Zeit")); [w.writerow(self.values.item(i,"values")) for i in self.values.get_children()]

if __name__=="__main__": App().mainloop()
