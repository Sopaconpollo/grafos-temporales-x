"""Figuras PDF vectoriales para el artículo."""
import argparse
from collections import defaultdict
import csv
from pathlib import Path

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import HexColor, white, Color

MONTHS = ("Ene.", "Feb.", "Mar.", "Abr.", "May.", "Jun.")
INK, MUTED, GRID = map(HexColor, ("#122e34", "#485e65", "#dce5e7"))
PALETTE = tuple(map(HexColor, ("#06776a", "#aa442e", "#1768a0", "#795647", "#865591")))


def rows(file):
    with file.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def begin(path, title, subtitle, h=225):
    c = Canvas(str(path), pagesize=(400,h))
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold",14)
    c.drawString(12,h-19,title)
    c.setFillColor(MUTED)
    c.setFont("Helvetica",10)
    c.drawString(12,h-33,subtitle)
    return c


def axes(c, labels, maximum, step, fmt):
    left,right,bottom,top = 48,382,53,175
    for value in range(0,maximum+1,step):
        y=bottom+(top-bottom)*value/maximum
        c.setStrokeColor(GRID)
        c.line(left,y,right,y)
        c.setFillColor(MUTED)
        c.setFont("Helvetica",9)
        c.drawRightString(left-7,y-3,fmt(value))
    xs = [left+20+i*(right-left-40)/(len(labels)-1) for i in range(len(labels))]
    for x,label in zip(xs,labels):
        c.drawCentredString(x,bottom-14,label)
    return xs, lambda value: bottom+(top-bottom)*value/maximum


def line(c, xs, y, vals, color, dash=()):
    c.setStrokeColor(color)
    c.setLineWidth(2)
    c.setDash(list(dash))
    for a,b,v,w in zip(xs,xs[1:],vals,vals[1:]):
        c.line(a,y(v),b,y(w))
    c.setDash()
    c.setFillColor(color)
    for x,v in zip(xs,vals):
        c.circle(x,y(v),3,stroke=0,fill=1)


def legend(c, entries):
    c.setFont("Helvetica",9)
    x=48
    for label,color in entries:
        c.setFillColor(color)
        c.circle(x,19,3,stroke=0,fill=1)
        c.setFillColor(INK)
        c.drawString(x+7,16,label)
        x+=c.stringWidth(label,"Helvetica",9)+24


def make(data, output):
    structure=defaultdict(list)
    for r in rows(data/"estructura.csv"):
        structure[r["capa"]].append(100*float(r["fraccion_cm"]))
    c=begin(output/"conectividad.pdf","La componente mayor por capa","Porcentaje de nodos en la componente mayor")
    labels=("Agregada","Menciones","Respuestas","Citas")
    xs,y=axes(c,MONTHS,100,25,lambda v:f"{v}%")
    for layer,color in zip(("all","mention","reply","quote"),PALETTE):
        line(c,xs,y,structure[layer],color)
    legend(c,zip(labels,PALETTE))
    c.save()

    scan=[r for r in rows(data/"volumen_igualado.csv") if r["metrica"]=="fraccion_cm"]
    c=begin(output/"volumen.pdf","Conectividad con el volumen igualado","120 submuestras de 433 publicaciones con interacción")
    xs,y=axes(c,MONTHS,100,25,lambda v:f"{v}%")
    c.setStrokeColor(PALETTE[0]); c.setLineWidth(1.5)
    for x,r in zip(xs,scan):
        lo,hi=(y(float(r[k])*100) for k in ("p05","p95"))
        c.line(x,lo,x,hi); c.line(x-4,lo,x+4,lo); c.line(x-4,hi,x+4,hi)
    line(c,xs,y,[100*float(r["mediana"]) for r in scan],PALETTE[0])
    line(c,xs,y,structure["all"],PALETTE[1],(4,3))
    legend(c,[("Mediana y percentiles 5–95",PALETTE[0]),("Red mensual completa",PALETTE[1])])
    c.save()

    scan=rows(data/"ari_modularidad.csv")
    c=begin(output/"persistencia.pdf","Continuidad entre particiones mensuales","ARI de modularidad sobre las cuentas compartidas")
    xs,y=axes(c,("Ene.–Feb.","Feb.–Mar.","Mar.–Abr.","Abr.–May.","May.–Jun."),100,25,lambda v:f"{v/100:.2f}".replace(".",","))
    line(c,xs,y,[100*float(r["ari"]) for r in scan],PALETTE[0])
    c.setFont("Helvetica-Bold",9)
    for x,r in zip(xs,scan):
        c.drawCentredString(x,y(float(r["ari"])*100)+8,r["compartidas"])
    legend(c,[("Etiquetas: número de cuentas compartidas",PALETTE[0])])
    c.save()

    content=defaultdict(list)
    for row in rows(data/"contenido.csv"):
        content[row["tipo"],row["etiqueta"]].append(100*float(row["proporcion"]))
    c=begin(output/"contenido.pdf","Nombres y temas en el texto","Porcentaje mensual de textos con coincidencia léxica",255)
    for i,month in enumerate(MONTHS):
        c.setFillColor(MUTED); c.setFont("Helvetica-Bold",9)
        c.drawCentredString(152+i*42,204,month)
    for j,((_,label),values) in enumerate(content.items()):
        ypos=182-j*19
        c.setFillColor(INK); c.setFont("Helvetica",9)
        c.drawRightString(128,ypos+3,label)
        for i,value in enumerate(values):
            x=132+i*42
            factor=min(value/60,1)
            c.setFillColor(Color(.92-.79*factor,.96-.49*factor,.95-.48*factor))
            c.rect(x,ypos,40,16,fill=1,stroke=0)
            c.setFillColor(white if factor>.62 else INK)
            c.drawCentredString(x+20,ypos+4,f"{value:.1f}".replace(".",","))
    c.save()


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("data",type=Path); p.add_argument("output",type=Path)
    args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    make(args.data,args.output)
