import java.io.*;
import java.util.*;
import loci.formats.ImageReader;
import loci.formats.MetadataTools;
import loci.formats.meta.IMetadata;
import loci.formats.FormatTools;
import ome.units.UNITS;

/** Bio-Formats adapter. Never modifies the acquisition. Zero-based series/channel/z. */
public class OirBridge {
  static String q(String s) { return "\""+s.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r")+"\""; }
  public static void main(String[] a) throws Exception {
    loci.common.DebugTools.setRootLevel("ERROR");
    ImageReader r=new ImageReader(); IMetadata m=MetadataTools.createOMEXMLMetadata();
    r.setMetadataStore(m); r.setId(a[1]);
    int s=Integer.parseInt(a[2]); r.setSeries(s);
    int c=Integer.parseInt(a[3]), z=Integer.parseInt(a[4]);
    if(c<0||c>=r.getSizeC()||z<0||z>=r.getSizeZ()) throw new IllegalArgumentException("Channel/Z outside source");
    if(r.isRGB()) throw new IllegalArgumentException("RGB acquisition is not supported");
    int type=r.getPixelType();
    String dtype=FormatTools.getPixelTypeString(type);
    if(!Arrays.asList("uint8","uint16","int16","uint32","int32","float","double").contains(dtype)) throw new IllegalArgumentException("Unsupported pixel type: "+dtype);
    String px=m.getPixelsPhysicalSizeX(s)==null?"null":m.getPixelsPhysicalSizeX(s).value(UNITS.MICROMETER).toString();
    String py=m.getPixelsPhysicalSizeY(s)==null?"null":m.getPixelsPhysicalSizeY(s).value(UNITS.MICROMETER).toString();
    String dt=m.getPixelsTimeIncrement(s)==null?"null":m.getPixelsTimeIncrement(s).value(UNITS.SECOND).toString();
    Double[] times=new Double[r.getSizeT()];
    for(int p=0;p<m.getPlaneCount(s);p++) {
      if(m.getPlaneTheC(s,p)==null||m.getPlaneTheZ(s,p)==null||m.getPlaneTheT(s,p)==null) continue;
      if(m.getPlaneTheC(s,p).getValue()==c&&m.getPlaneTheZ(s,p).getValue()==z&&m.getPlaneDeltaT(s,p)!=null)
        times[m.getPlaneTheT(s,p).getValue()]=m.getPlaneDeltaT(s,p).value(UNITS.SECOND).doubleValue();
    }
    ArrayList<String> files=new ArrayList<>(); for(String f:r.getUsedFiles()) files.add(q(f));
    String json="{\"series_count\":"+r.getSeriesCount()+",\"series\":"+s+",\"channels\":"+r.getSizeC()+",\"z_planes\":"+r.getSizeZ()+",\"channel\":"+c+",\"z\":"+z+",\"shape\":["+r.getSizeT()+","+r.getSizeY()+","+r.getSizeX()+"],\"dtype\":"+q(dtype)+",\"little_endian\":"+r.isLittleEndian()+",\"pixel_x_um\":"+px+",\"pixel_y_um\":"+py+",\"interval_s\":"+dt+",\"plane_times_s\":"+Arrays.toString(times)+",\"used_files\":["+String.join(",",files)+"]}";
    System.out.println("ATP_META "+json);
    if(a[0].equals("convert")) {
      try(OutputStream out=new BufferedOutputStream(new FileOutputStream(a[5]))) {
        for(int t=0;t<r.getSizeT();t++) {out.write(r.openBytes(r.getIndex(z,c,t))); if(t%50==0) System.out.println("ATP_FRAME "+t);}
      }
    }
    r.close();
  }
}
