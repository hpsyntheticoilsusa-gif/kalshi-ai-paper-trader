"""Create self-contained PNG icons using only Python's standard library."""
import math,struct,zlib,pathlib
DOCS=pathlib.Path(__file__).parent/"docs"
def chunk(kind,data):return struct.pack("!I",len(data))+kind+data+struct.pack("!I",zlib.crc32(kind+data)&0xffffffff)
def make(size):
    rows=[]
    vertices=[(.18,.69),(.32,.59),(.43,.64),(.55,.44),(.66,.51),(.79,.30)]
    verts=[(x*size,y*size) for x,y in vertices]
    for y in range(size):
        row=bytearray([0])
        for x in range(size):
            u=x/size;v=y/size
            r,g,b=(13,24,29)
            # Very faint tech grid
            if x%max(1,size//9)==0 or y%max(1,size//9)==0:g+=8
            # simple stepped price columns
            bars=[(.22,.77),(.35,.68),(.49,.61),(.63,.53),(.77,.40)]
            for bx,top in bars:
                if abs(u-bx)<.034 and top<v<.83:g+=22;b+=7
            # upward zigzag with vibrant green line
            dist=1e9
            for (ax,ay),(bx,by) in zip(verts,verts[1:]):
                dx=bx-ax;dy=by-ay
                t=max(0,min(1,((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
                dist=min(dist,math.hypot(x-ax-t*dx,y-ay-t*dy))
            # Arrow head two descending edges at top right
            tip=(.83*size,.16*size)
            for aa,bb in [((.79*size,.30*size),tip),((.73*size,.20*size),tip),((.92*size,.22*size),tip)]:
                ax,ay=aa;bx,by=bb;dx=bx-ax;dy=by-ay
                t=max(0,min(1,((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
                dist=min(dist,math.hypot(x-ax-t*dx,y-ay-t*dy))
            if dist<size*.035:g+=int(60*(1-dist/(size*.035)));b+=5
            if dist<size*.014:r,g,b=(38,238,122)
            row.extend((min(255,r),min(255,g),min(255,b),255))
        rows.append(bytes(row))
    raw=b''.join(rows);ihdr=struct.pack("!2I5B",size,size,8,6,0,0,0)
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',ihdr)+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b'')
    (DOCS/("icon-%d.png"%size)).write_bytes(png)
for sz in (192,512):make(sz)
print("PWA PNG icons generated")
