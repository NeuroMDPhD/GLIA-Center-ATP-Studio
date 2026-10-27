from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio.v2 as imageio

def limits(movie):
    values=np.asarray(movie[::max(1,len(movie)//40),::3,::3])
    lo,hi=np.percentile(values,[1,99.5]); return float(lo),float(max(hi,lo+1))

def grayscale(a,lo,hi): return np.uint8(np.clip((np.asarray(a,dtype=float)-lo)/(hi-lo),0,1)*255)

def movie_mp4(movie, path, times, px, job, event_voxels=None, fps=15):
    lo,hi=limits(movie); n,h,w=movie.shape
    writer=imageio.get_writer(str(path),fps=fps,codec='libx264',quality=7,macro_block_size=1,pixelformat='yuv420p')
    # Even padding is display only; measurements always use original dimensions.
    try:
        for i,a in enumerate(movie):
            job.check(); rgb=np.repeat(grayscale(a,lo,hi)[...,None],3,axis=2)
            if event_voxels:
                for eid,v in event_voxels.items():
                    vv=v[v[:,0]==i]
                    if len(vv): rgb[vv[:,1],vv[:,2]]=np.array([24,220,173],dtype=np.uint8)
            im=Image.new('RGB',(w+w%2,h+h%2));im.paste(Image.fromarray(rgb))
            draw=ImageDraw.Draw(im); draw.rectangle((0,0,min(w,260),20),fill='black')
            draw.text((6,4),f'{times[i]:.2f} s  |  frame {i+1}/{n}',fill='white')
            bar=min(int(round(50/px)),w//3)
            if bar>0:
                draw.line((w-15-bar,h-18,w-15,h-18),fill='white',width=3)
                draw.text((w-15-bar,h-34),f'{bar*px:.1f} um',fill='white')
            writer.append_data(np.asarray(im))
            if i%100==0: job.log(f'Writing movie / 動画保存: {i+1}/{n} frames')
    finally: writer.close()

def trace_png(path, times, traces, labels, title, drug_s=None, span=None):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    fig=Figure(figsize=(9,3.5),dpi=150);FigureCanvasAgg(fig);ax=fig.subplots()
    for trace,label in zip(traces,labels): ax.plot(times,trace,lw=1.1,label=label)
    if span: ax.axvspan(*span,alpha=.1,color='#11a788')
    if drug_s is not None: ax.axvline(drug_s,color='#d28b30',ls='--',label='Treatment')
    ax.set(xlabel='Time (s)',ylabel='Signal',title=title);ax.spines[['top','right']].set_visible(False)
    if len(labels)<=12: ax.legend(frameon=False,fontsize=8)
    fig.tight_layout();fig.savefig(path)
