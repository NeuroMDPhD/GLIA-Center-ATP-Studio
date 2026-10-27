package va.vt.cbilAQuA2.run;

import java.io.*;
import java.util.*;
import java.lang.reflect.*;
import va.vt.cbilAQuA2.*;
import va.vt.cbilAQuA2.fea.*;

/** Thin headless adapter around unmodified upstream AQuA2 helper algorithms. */
public class StudioBridge {
  static void phase(String s) {System.out.println("ATP_PHASE "+s); System.out.flush();}
  public static void main(String[] a) throws Exception {
    Properties p=new Properties(); try(InputStream in=new FileInputStream(a[0])){p.load(in);}
    Opts o=new Opts(1);
    for(String k:p.stringPropertyNames()) {
      try {Field f=Opts.class.getField(k); String v=p.getProperty(k);
        if(f.getType()==int.class) f.setInt(o,Integer.parseInt(v));
        if(f.getType()==float.class) f.setFloat(o,Float.parseFloat(v));
        if(f.getType()==boolean.class) f.setBoolean(o,Boolean.parseBoolean(v));
      } catch(NoSuchFieldException ignored) {}
    }
    o.singleChannel=true; o.detectGlo=false; o.needTemp=true; o.needSpa=true;
    o.ignoreTau=false; o.movAvgWin=Math.min(o.movAvgWin,o.T); o.cut=Math.min(o.cut,o.T);
    String out=a[2]+File.separator; new File(out).mkdirs();
    phase("read"); float[][][] dat=new float[o.H][o.W][o.T];
    float mn=Float.POSITIVE_INFINITY,mx=Float.NEGATIVE_INFINITY;
    try(DataInputStream in=new DataInputStream(new BufferedInputStream(new FileInputStream(a[1])))) {
      for(int t=0;t<o.T;t++) for(int y=0;y<o.H;y++) for(int x=0;x<o.W;x++) {
        float v=in.readFloat(); if(!Float.isFinite(v)) throw new IOException("Non-finite input pixels");
        dat[y][x][t]=v; mn=Math.min(mn,v); mx=Math.max(mx,v);
      }
    }
    if(mx<=mn) throw new IllegalArgumentException("Constant movie: no noise estimate possible");
    o.minValueDat=mn; o.maxValueDat=mx;
    for(int y=0;y<o.H;y++) for(int x=0;x<o.W;x++) for(int t=0;t<o.T;t++) dat[y][x][t]=(dat[y][x][t]-mn)/(mx-mn);
    boolean[][] mask=new boolean[o.H][o.W]; for(boolean[] row:mask) Arrays.fill(row,true);
    phase("baseline_noise"); float[][][] df=Step1Helper.baselineRemoveAndNoiseEstimation(dat,mask,1,out,o);
    phase("active_regions"); HashMap<Integer,ArrayList<int[]>> ar=Step2Helper.acDetect(df,new int[o.H][o.W][o.T],mask,1,o);
    HashMap<Integer,ArrayList<int[]>> ev=new HashMap<>();
    if(!ar.isEmpty()) {
      phase("temporal_segmentation"); Step3HelperResult se=Step3Helper.seDetection(df,dat,ar,o);
      if(!se.seLst.isEmpty()) {
        phase("spatial_segmentation"); Step4Res r=Step4Helper.se2evtTop(df,se.seLst,se.evtLst,se.seLabel,se.majorInfo,o); ev=r.evtLst;
      }
    }
    phase("features"); FeatureTopResult ft=ev.isEmpty()?null:Step6Helper.getFeaturesTop(dat,ev,o);
    try(DataOutputStream b=new DataOutputStream(new BufferedOutputStream(new FileOutputStream(out+"events.bin")))) {
      b.writeInt(0x41545031); b.writeInt(ev.size()); b.writeInt(o.T); b.writeInt(o.H); b.writeInt(o.W);
      for(int id=1;id<=ev.size();id++) {
        ArrayList<int[]> vox=ev.get(id); b.writeInt(id); b.writeInt(vox.size());
        for(int[] v:vox) {b.writeInt(v[2]); b.writeInt(v[0]); b.writeInt(v[1]);}
        int[] rg=ft.ftsLst.curve.rgt1.get(id); b.writeInt(rg[0]); b.writeInt(rg[1]);
        for(int t=0;t<o.T;t++) b.writeFloat(ft.dffMat[id-1][t][0]);
        for(int t=0;t<o.T;t++) b.writeFloat(ft.dffMat[id-1][t][1]);
      }
    }
    try(PrintWriter csv=new PrintWriter(out+"aqua_features.csv","UTF-8")) {
      csv.println("event_id,aqua_peak_dff,aqua_fwhm_s,aqua_rise_10_90_s,aqua_fall_90_10_s,aqua_decay_tau_s,aqua_auc_dff_frames");
      for(int id=1;id<=ev.size();id++) {Curve c=ft.ftsLst.curve; csv.println(id+","+c.dffMax.get(id)+","+c.width55.get(id)+","+c.rise19.get(id)+","+c.fall91.get(id)+","+c.decayTau.get(id)+","+c.dffAUC.get(id));}
    }
    Properties effective=new Properties();
    for(Field f:Opts.class.getFields()) if(f.getType().isPrimitive()) effective.setProperty(f.getName(),String.valueOf(f.get(o)));
    try(OutputStream os=new FileOutputStream(out+"effective.properties")){effective.store(os,"Effective AQuA2 options");}
    phase("complete "+ev.size()); System.exit(0);
  }
}
