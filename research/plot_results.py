import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

root = Path(__file__).resolve().parent
figdir = root / "figures"
figdir.mkdir(exist_ok=True)
data = json.loads((root / "cnn-results/results.json").read_text())
results = data["results"]
names = list(results)
colors = ["#657383", "#007b79", "#31598e", "#bd6619"]
plt.rcParams.update({"font.size":10, "axes.spines.top":False,"axes.spines.right":False,
                     "axes.titlelocation":"left","axes.labelcolor":"#253342","text.color":"#1a2c40",
                     "pdf.fonttype":42,"svg.fonttype":"none"})
def save(fig, name):
    for fmt in ("pdf", "png"):
        fig.savefig(figdir / f"{name}.{fmt}",dpi=200,bbox_inches="tight",pad_inches=.15)
    plt.close(fig)

fig,axs = plt.subplots(1,2,figsize=(8.1,3.1),gridspec_kw={"width_ratios":[1,1.15]},layout="constrained")
labels=["Length only","ByteCNN 2D","Sequence 1D","Separable 2D"]
ax=axs[0]
for i,name in enumerate(names):
    v=results[name]["correct"]/results[name]["n"]
    ax.barh(i,v,color=colors[i],height=.5)
    ax.text((v - .035 if v >= .9 else v + .025),i,f"{100*v:g}%",va="center",ha="left" if v<.9 else "right",color="white" if v>=.9 else "#17232c",weight="bold",fontsize=9)
ax.set(yticks=range(4),yticklabels=labels,xlim=(0,1),xticks=[0,.5,1],xticklabels=["0%","50%","100%"],xlabel="Test accuracy (40 files)")
ax.invert_yaxis()
ax.set_title("A   Held-out format recognition",fontsize=10,weight="bold")
rows=list(csv.DictReader((root/"cnn-results/validation.csv").open()))
ax=axs[1]
for i,name in enumerate(names[1:],1):
    ys=[float(r["validation_loss"]) for r in rows if r["model"]==name]
    ax.plot(range(1,len(ys)+1),ys,label=labels[i],lw=1.8,color=colors[i],marker=["","o","s","^"][i],ms=3)
ax.set(xlabel="Training epoch",ylabel="Validation cross-entropy",xticks=[1,4,7,10])
ax.legend(fontsize=7,frameon=False);ax.set_title("B   Learning over ten epochs",fontsize=10,weight="bold")
save(fig,"cnn-comparison")

fig,axs=plt.subplots(1,3,figsize=(8.3,2.9),layout="constrained")
for ax,name in zip(axs,names[1:]):
    vals=np.array(results[name]["confusion"])
    ax.imshow(vals,cmap="Blues",vmin=0,vmax=8)
    for row in range(5):
        for col in range(5):
            ax.text(col,row,str(vals[row,col]),ha="center",va="center",color="white" if vals[row,col]>4 else "#10324b",fontsize=9)
    ax.set(xticks=range(5),xticklabels=data["classes"],yticks=range(5),yticklabels=data["classes"],xlabel="Predicted format")
    ax.tick_params(labelsize=7);ax.set_title(name,fontsize=10,weight="bold")
axs[0].set_ylabel("Actual format")
save(fig,"cnn-confusion")

sched=json.loads((root/"scheduling/results.json").read_text())["results"]
order=["fifo","edf","rule","lightgbm","tgn"]
fig,axs=plt.subplots(1,2,figsize=(8,3.3),layout="constrained")
for ax,metric,lab,fmt in [(axs[0],"mean_wait_seconds","Mean queue wait (s)",".1f"),(axs[1],"deadline_misses","Missed deadlines out of 720","d")]:
    vals=[sched[k][metric] for k in order]
    ax.barh(range(5),vals,color=["#718497","#24697b","#719a8f","#376aa5","#35928c"],height=.56)
    for i,v in enumerate(vals):
        ax.text(v-14,i,format(v,fmt),va="center",ha="right",fontsize=9,color="white",weight="bold")
    ax.set(xlim=(0,720),yticks=range(5),yticklabels=["FIFO","EDF","Rule","LightGBM","TGN"],xlabel=lab);ax.invert_yaxis()
save(fig,"schedule-outcomes")
