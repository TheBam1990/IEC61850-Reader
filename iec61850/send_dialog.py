from __future__ import annotations
import tkinter as tk
from tkinter import messagebox, ttk

class SendDialog(tk.Toplevel):
    FCS=("ST","MX","SP","SV","CF","DC","SG","SE","OR","BL","EX","CO","RP","BR")
    TYPES=("bool","int","uint","float","string")
    def __init__(self,parent,read_cb,write_cb,control_cb,initial_ref=""):
        super().__init__(parent); self.title("IEC61850 senden / lesen"); self.geometry("680x410"); self.transient(parent)
        book=ttk.Notebook(self); book.pack(fill=tk.BOTH,expand=True,padx=10,pady=10)
        self.ref=tk.StringVar(value=initial_ref); self.fc=tk.StringVar(value="MX"); self.typ=tk.StringVar(value="bool"); self.value=tk.StringVar(value="0")
        rw=ttk.Frame(book,padding=12); book.add(rw,text="Lesen / Schreiben")
        self._fields(rw)
        ttk.Button(rw,text="Lesen",command=lambda:self._safe(read_cb,False)).grid(row=2,column=0,padx=4,pady=14,sticky="w")
        ttk.Button(rw,text="Wert schreiben",command=lambda:self._confirm_write(write_cb)).grid(row=2,column=1,padx=4,pady=14,sticky="w")
        ctl=ttk.Frame(book,padding=12); book.add(ctl,text="Steuern")
        self.ctl_ref=tk.StringVar(value=initial_ref); self.ctl_type=tk.StringVar(value="bool"); self.ctl_value=tk.StringVar(value="0"); self.origin=tk.StringVar(value="3")
        self.test=tk.BooleanVar(); self.interlock=tk.BooleanVar(value=True); self.synchro=tk.BooleanVar()
        for col,(label,var) in enumerate((("Control-Objekt",self.ctl_ref),("Typ",self.ctl_type),("Wert",self.ctl_value),("Origin-Kategorie",self.origin))):
            ttk.Label(ctl,text=label).grid(row=0,column=col,sticky="w",padx=4)
            widget = ttk.Combobox(ctl,textvariable=var,values=self.TYPES,state="readonly",width=16) if label=="Typ" else ttk.Entry(ctl,textvariable=var,width=16)
            widget.grid(row=1,column=col,padx=4,sticky="ew")
        ttk.Checkbutton(ctl,text="Test",variable=self.test).grid(row=2,column=0,sticky="w",pady=10)
        ttk.Checkbutton(ctl,text="Interlock-Prüfung",variable=self.interlock).grid(row=2,column=1,sticky="w")
        ttk.Checkbutton(ctl,text="Synchro-Prüfung",variable=self.synchro).grid(row=2,column=2,sticky="w")
        for col,(label,action) in enumerate((("Auswählen","select"),("Ausführen","operate"),("Abbrechen","cancel"))): ttk.Button(ctl,text=label,command=lambda a=action:self._control(control_cb,a)).grid(row=3,column=col,padx=4,pady=12,sticky="w")
        ttk.Label(ctl,text="Steuerbefehle können reale Schalthandlungen auslösen.",foreground="#9b2c2c").grid(row=4,column=0,columnspan=4,sticky="w")
    def _fields(self,p):
        for col,(label,var) in enumerate((("Objektreferenz",self.ref),("FC",self.fc),("Typ",self.typ),("Wert",self.value))):
            ttk.Label(p,text=label).grid(row=0,column=col,sticky="w",padx=4)
            values=self.FCS if label=="FC" else self.TYPES if label=="Typ" else ()
            widget=ttk.Combobox(p,textvariable=var,values=values,state="readonly",width=14) if values else ttk.Entry(p,textvariable=var,width=35)
            widget.grid(row=1,column=col,padx=4,sticky="ew")
    def _safe(self,cb,_danger):
        try: cb(self.ref.get(),self.fc.get())
        except Exception as e: messagebox.showerror("IEC61850",str(e),parent=self)
    def _confirm_write(self,cb):
        if messagebox.askyesno("IEC61850","Wert wirklich schreiben?",icon="warning",default="no",parent=self):
            try: cb(self.ref.get(),self.fc.get(),self.typ.get(),self.value.get())
            except Exception as e: messagebox.showerror("IEC61850",str(e),parent=self)
    def _control(self,cb,action):
        if not messagebox.askyesno("IEC61850",f"Steueraktion {action} wirklich senden?",icon="warning",default="no",parent=self): return
        try: cb(self.ctl_ref.get(),self.ctl_type.get(),self.ctl_value.get(),action,int(self.origin.get()),self.test.get(),self.interlock.get(),self.synchro.get())
        except Exception as e: messagebox.showerror("IEC61850",str(e),parent=self)
