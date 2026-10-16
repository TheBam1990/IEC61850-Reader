import threading, tkinter as tk
from tkinter import filedialog, messagebox, ttk

class MonitorDialog(tk.Toplevel):
    def __init__(self,parent,backend,target,log):
        super().__init__(parent); self.title("Reports, GOOSE und TLS"); self.geometry("760x520"); self.backend=backend; self.target=target; self.log=log; self.processes=[]
        book=ttk.Notebook(self); book.pack(fill="both",expand=True,padx=10,pady=10)
        report=ttk.Frame(book,padding=12); book.add(report,text="Reports")
        self.rcb=tk.StringVar(); self.dataset=tk.StringVar()
        for r,(label,var) in enumerate((("RCB-Referenz",self.rcb),("DataSet-Referenz",self.dataset))): ttk.Label(report,text=label).grid(row=r,column=0,sticky="w",pady=4); ttk.Entry(report,textvariable=var,width=65).grid(row=r,column=1,sticky="ew",padx=4)
        ttk.Button(report,text="Dauerhaft abonnieren",command=self.start_report).grid(row=2,column=0,pady=12); ttk.Button(report,text="Stoppen",command=self.stop).grid(row=2,column=1,sticky="w")
        goose=ttk.Frame(book,padding=12); book.add(goose,text="GOOSE")
        self.interface=tk.StringVar(); ttk.Label(goose,text="Npcap-Netzwerkadapter-ID").grid(row=0,column=0,sticky="w"); ttk.Entry(goose,textvariable=self.interface,width=55).grid(row=1,column=0,sticky="ew"); ttk.Button(goose,text="GOOSE-Mitschnitt starten",command=self.start_goose).grid(row=2,column=0,sticky="w",pady=12); ttk.Label(goose,text="Erfordert Npcap im WinPcap-kompatiblen Modus. Adapter-ID z. B. aus Wireshark/Npcap übernehmen.",foreground="#9b2c2c",wraplength=680).grid(row=3,column=0,sticky="w")
        tls=ttk.Frame(book,padding=12); book.add(tls,text="TLS / IEC 62351")
        self.tls_enabled=tk.BooleanVar(); self.ca=tk.StringVar(); self.cert=tk.StringVar(); self.key=tk.StringVar()
        ttk.Checkbutton(tls,text="TLS für neue MMS-Aktionen aktivieren",variable=self.tls_enabled,command=self.apply_tls).grid(row=0,column=0,columnspan=3,sticky="w",pady=4)
        for row,(label,var) in enumerate((("CA-Zertifikat",self.ca),("Clientzertifikat",self.cert),("Privater Schlüssel",self.key)),1):
            ttk.Label(tls,text=label).grid(row=row,column=0,sticky="w",pady=4); ttk.Entry(tls,textvariable=var,width=57).grid(row=row,column=1,padx=4); ttk.Button(tls,text="...",command=lambda v=var:self.pick(v)).grid(row=row,column=2)
        ttk.Button(tls,text="TLS-Einstellung übernehmen",command=self.apply_tls).grid(row=5,column=0,pady=12,sticky="w")
        self.protocol("WM_DELETE_WINDOW",self.close)
    def pick(self,var):
        path=filedialog.askopenfilename(parent=self)
        if path: var.set(path)
    def apply_tls(self):
        if self.tls_enabled.get() and not all((self.ca.get(),self.cert.get(),self.key.get())): return
        self.backend.set_tls(self.tls_enabled.get(),self.ca.get(),self.cert.get(),self.key.get()); self.log("TLS-Konfiguration aktualisiert")
    def pump(self,p):
        for line in p.stdout or (): self.after(0,lambda x=line.rstrip():self.log(x))
    def start_report(self):
        try:
            h,p=self.target(); proc=self.backend.start_report(h,p,self.rcb.get(),self.dataset.get()); self.processes.append(proc); threading.Thread(target=self.pump,args=(proc,),daemon=True).start()
        except Exception as e: messagebox.showerror("IEC61850",str(e),parent=self)
    def start_goose(self):
        try:
            proc=self.backend.start_goose(self.interface.get()); self.processes.append(proc); threading.Thread(target=self.pump,args=(proc,),daemon=True).start()
        except Exception as e: messagebox.showerror("IEC61850",str(e),parent=self)
    def stop(self):
        for p in self.processes:
            if p.poll() is None: p.terminate()
        self.processes=[]; self.log("Monitore gestoppt")
    def close(self): self.stop(); self.destroy()
