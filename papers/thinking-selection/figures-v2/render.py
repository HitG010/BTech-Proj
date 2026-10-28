"""Additive report-only figures, sized for a 6.6-inch manuscript column."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/thinking-selection-v2-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
INK='#172B40';GRAY='#4A5968';BLUE='#236B8E';TEAL='#147D74';ORANGE='#B35A20';LIGHT='#DCE4EA'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def txt(ax,x,y,s,size=10,weight='normal',color=INK,ha='left',va='center',**kw):
    return ax.text(x,y,s,fontsize=size,fontweight=weight,color=color,ha=ha,va=va,linespacing=1.3,**kw)
def box(ax,x,y,w,h,face='#F4F7FA',edge=LIGHT):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.025,rounding_size=0.06',facecolor=face,edgecolor=edge,lw=1))
def arrow(ax,a,b,dashed=False):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=12,lw=1.2,color=GRAY,linestyle='--' if dashed else '-'))
def page(height,title):
    fig=plt.figure(figsize=(6.6,height),facecolor='white');ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,6.6),ylim=(0,height));ax.axis('off')
    txt(ax,.15,height-.25,title,14,'bold')
    return fig,ax

def decision(s):
    fig,ax=page(5.8,s['title'])
    box(ax,.15,4.57,1.00,.65);txt(ax,.65,4.895,'Question',11,ha='center')
    box(ax,1.47,4.57,1.35,.65);txt(ax,2.145,4.895,'Direct draft D\nPay direct cost',10,ha='center')
    box(ax,3.14,4.57,1.16,.65,edge=BLUE);txt(ax,3.72,4.895,'Selector',11,'bold',ha='center')
    arrow(ax,(1.18,4.895),(1.44,4.895));arrow(ax,(2.85,4.895),(3.11,4.895))
    box(ax,4.85,4.92,1.53,.56,face='#EAF3F7',edge=BLUE);txt(ax,5.615,5.20,'Accept D\nCost: $C_D$',10,ha='center')
    box(ax,4.85,3.96,1.53,.72,face='#E7F3F0',edge=TEAL);txt(ax,5.615,4.32,'Fresh thinking T\nQuestion only\nCost: $C_D+C_T$',10,ha='center')
    arrow(ax,(4.33,5.02),(4.82,5.20));arrow(ax,(4.33,4.72),(4.82,4.34))
    txt(ax,.15,4.09,'Choose before seeing T.\nThinking does not revise D.',10,color=GRAY)
    txt(ax,.15,3.48,'Recorded outcomes on the repeat panel',12,'bold')
    txt(ax,.15,3.15,'400 pairs from 50 questions; one D and one T per pair',10,color=GRAY)
    txt(ax,2.80,2.72,'Thinking correct',10,'bold',ha='center')
    txt(ax,5.12,2.72,'Thinking incorrect',10,'bold',ha='center')
    txt(ax,.15,2.12,'Direct\ncorrect',10,'bold')
    txt(ax,.15,1.12,'Direct\nincorrect',10,'bold')
    for c,(x,y,fc) in zip(s['cells'],[(1.69,1.69,'#EDF2F6'),(4.01,1.69,'#F9EDE5'),(1.69,.69,'#E3F2EC'),(4.01,.69,'#EDF2F6')]):
        box(ax,x,y,2.20,.85,fc)
        txt(ax,x+.15,y+.54,str(c['count']),23,'bold',color=TEAL if c['label']=='Rescues' else ORANGE if c['label']=='Harms' else INK)
        txt(ax,x+.15,y+.19,c['label'],11)
    txt(ax,.15,.25,'Scorer-defined counts; cell areas are schematic.',10,color=GRAY)
    return fig

def design(s):
    fig,ax=page(6.5,s['title'])
    box(ax,.15,3.15,6.28,2.80,edge=BLUE)
    txt(ax,.30,5.72,'Primary panel: 50 questions',12,'bold',color=BLUE)
    txt(ax,.30,5.40,'8 draws per mode × 2 modes = 800 responses',11)
    txt(ax,.30,5.10,'400 paired states; draws A = 0–3 and B = 4–7',10,color=GRAY)
    txt(ax,.30,4.71,'One outer fold, four-draw A → B direction',10,'bold')
    box(ax,.33,3.79,2.56,.65,face='#EAF3F7',edge=BLUE)
    txt(ax,1.61,4.12,'Fit on 40 questions\nUse draw half A',11,ha='center')
    box(ax,3.50,3.79,2.58,.65,face='#E7F3F0',edge=TEAL)
    txt(ax,4.79,4.12,'Test on 10 excluded questions\nUse draw half B',10,ha='center')
    arrow(ax,(2.94,4.12),(3.45,4.12))
    txt(ax,.30,3.44,'Repeat over five question folds; also evaluate B → A.',10)
    txt(ax,.30,2.83,'Later controls and post-hoc checks reuse these 50 questions.',10,'bold')
    box(ax,.15,.53,3.00,1.98,edge=BLUE)
    txt(ax,.30,2.25,'Separate panel: 64 questions',11,'bold')
    txt(ax,.30,1.95,'Two solvers; 512 responses',10)
    box(ax,.31,.73,2.65,.87,face='#EDF2F6')
    txt(ax,.46,1.35,'Cap subset: 11 of the 64',10,'bold')
    txt(ax,.46,1.06,'18 matched pairs; 2k vs 4k cap',10)
    box(ax,3.67,.53,2.76,1.98,edge=TEAL)
    txt(ax,3.82,2.25,'Fresh guard: 228 questions',11,'bold')
    txt(ax,3.82,1.87,'Refit on 128 development states,\nthen freeze before collection.',10)
    txt(ax,3.82,1.24,'228 direct + 1 thinking response\nOnly one action changes.',10)
    arrow(ax,(3.18,1.53),(3.64,1.53),True)
    txt(ax,.15,.23,'The dashed link is design influence; the fresh questions are disjoint.',10,color=GRAY)
    return fig

def utility(s):
    fig=plt.figure(figsize=(6.6,4.7),facecolor='white')
    fig.text(.023,.94,s['title'],fontsize=14,weight='bold',color=INK)
    fig.text(.023,.875,'A  Primary learner vs selected simple baseline',fontsize=11,weight='bold',color=ORANGE)
    fig.text(.023,.595,'B  Later controls vs confidence',fontsize=11,weight='bold',color=BLUE)
    labels=[['Combined Ridge'],['CPU controls','Compact neural','CLM / raw encoder']]
    for panel,(bottom,height),color,names in zip(s['panels'],[(.66,.14),(.20,.28)],[ORANGE,BLUE],labels):
        ax=fig.add_axes([.31,bottom,.64,height]);n=len(panel['rows'])
        ax.set(xlim=(-.06,.02),ylim=(-.5,n-.5));ax.invert_yaxis()
        ax.axvspan(-.06,0,facecolor='#F2F5F8',zorder=0)
        ax.axvline(0,color=GRAY,lw=1.1,ls='--')
        ax.set_yticks(range(n),names);ax.tick_params(axis='y',length=0,labelsize=11,pad=8)
        ax.set_xticks([-.06,-.04,-.02,0,.02]);ax.tick_params(axis='x',labelsize=10)
        ax.grid(axis='x',color=LIGHT,lw=.6)
        for side in ['top','right','left']:ax.spines[side].set_visible(False)
        ax.spines['bottom'].set_color(LIGHT)
        for y,row in enumerate(panel['rows']):
            mean,lo,hi=[float(row[x]) for x in ['mean','low','high']]
            ax.errorbar(mean,y,xerr=[[mean-lo],[hi-mean]],fmt='D' if n==1 else 'o',color=color,markersize=7,capsize=4,elinewidth=1.7)
        if n==1:ax.tick_params(axis='x',labelbottom=False)
        else:ax.set_xlabel('Utility difference at $\\lambda=.05$',fontsize=11,labelpad=7)
    fig.text(.31,.515,'Negative: favors comparator',fontsize=10,color=GRAY)
    fig.text(.023,.027,'Reported conditional 90% intervals; fixed fits and actions.',fontsize=10,color=GRAY)
    return fig

def diagnostic(s):
    fig=plt.figure(figsize=(6.6,5.9),facecolor='white')
    fig.text(.023,.948,s['title'],fontsize=14,weight='bold',color=INK)
    fig.text(.023,.894,'64 shared questions; 128 pairs per solver',fontsize=11,color=GRAY)
    colors=[BLUE,ORANGE,TEAL];names=['Accept direct','Always escalate','Confidence'];markers=['s','^','o']
    for panel,bottom in zip(s['panels'],[.54,.18]):
        fig.text(.023,bottom+.265,panel['solver'],fontsize=12,weight='bold',color=INK)
        fig.text(.37,bottom+.265,f"{panel['positive_questions']}/64: positive gain in either draw",fontsize=10,color=GRAY)
        a=fig.add_axes([.255,bottom,.285,.205]);t=fig.add_axes([.64,bottom,.325,.205])
        for ax in [a,t]:
            ax.set_ylim(2.55,-.55);ax.grid(axis='x',color=LIGHT,lw=.6);ax.set_axisbelow(True)
            for side in ['top','right','left']:ax.spines[side].set_visible(False)
            ax.spines['bottom'].set_color(LIGHT);ax.tick_params(axis='both',length=0,labelsize=10)
        a.set(xlim=(50,100),xticks=[50,75,100]);t.set(xlim=(0,2400),xticks=[0,1000,2000])
        a.set_yticks(range(3),names);a.tick_params(axis='y',pad=8);t.set_yticks([])
        for y,(point,c,m) in enumerate(zip(panel['points'],colors,markers)):
            acc=float(point['accuracy']);tokens=float(point['tokens'])
            a.scatter(acc,y,color=c,marker=m,s=55,zorder=3)
            a.annotate(point['accuracy'],(acc,y),xytext=(5,-3),textcoords='offset points',ha='left',fontsize=10,color=INK)
            t.barh(y,tokens,color=c,height=.32,alpha=.85)
            t.text(tokens+40,y,point['tokens'],fontsize=10,va='center',color=INK)
        if bottom<.3:
            a.set_xlabel('Scored accuracy (%)',fontsize=10,labelpad=7)
            t.set_xlabel('Output tokens / state',fontsize=10,labelpad=7)
    fig.text(.023,.035,'Point estimates only. Tokens are not equal compute across sizes.',fontsize=10,color=GRAY)
    return fig

if __name__=='__main__':
    manifest=json.loads((HERE/'freeze.json').read_text())
    for rel,h in manifest['sha256'].items():
        p=ROOT/rel
        if sha(p)!=h:raise RuntimeError('Changed input: '+rel)
        if rel.startswith('papers/thinking-selection/figures-v2/') and p.read_bytes()!=subprocess.check_output(['git','show','HEAD:'+rel],cwd=ROOT):raise RuntimeError('Uncommitted export input: '+rel)
    data=json.loads((HERE/'display-inputs.json').read_text())
    out=HERE/'output'
    if out.exists():raise RuntimeError('Preserve completed export; use an additive revision')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'text.color':INK,'axes.labelcolor':INK,'pdf.fonttype':42,'svg.fonttype':'none','svg.hashsalt':'thinking-selection-v2'})
    outputs=[]
    for spec,draw in zip(data['figures'],[decision,design,utility,diagnostic]):
        fig=draw(spec);fig.canvas.draw()
        renderer=fig.canvas.get_renderer()
        for obj in fig.findobj(match=matplotlib.text.Text):
            if not obj.get_visible() or not obj.get_text():continue
            b=obj.get_window_extent(renderer)
            if b.x0<-.5 or b.y0<-.5 or b.x1>fig.bbox.width+.5 or b.y1>fig.bbox.height+.5:raise RuntimeError('Text outside '+spec['id']+': '+obj.get_text())
        for fmt in ['pdf','svg','png']:
            p=out/fmt/(spec['id']+'.'+fmt);p.parent.mkdir(parents=True,exist_ok=True)
            md={'Creator':'Report-only illustrative export v2','Title':spec['title']}
            if fmt=='pdf':md.update(CreationDate=None,ModDate=None,Subject=spec['caption'])
            elif fmt=='svg':md.update(Date=None,Description=spec['caption'])
            else:md['Description']=spec['caption']
            fig.savefig(p,format=fmt,dpi=220,metadata=md)
            outputs.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p)})
        plt.close(fig)
    (HERE/'export-record.json').write_text(json.dumps({'freeze_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),'outputs':outputs,'no_reestimation':True},indent=2)+'\n')
    print('Exported 12 files from frozen report values.')
