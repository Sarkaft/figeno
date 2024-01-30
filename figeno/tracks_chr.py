import matplotlib.patches as patches
import numpy as np
import pandas as pd
import matplotlib.colors as mcolors
import importlib_resources as resources
import colorsys

import figeno.data
from figeno.tracks_utils import split_box, draw_bounding_box , interpolate_polar_vertices, compute_rotation_text

class chr_track:
    def __init__(self,style="Default",unit="kb",ticks_pos="below",no_margin=False,reference="hg19",cytobands_file="",
                 fontscale=1,bounding_box=False,height=12,margin_above=1.5):
        self.style=style
        self.unit=unit
        self.ticks_pos=ticks_pos
        self.no_margin=no_margin
        self.reference=reference
        self.fontscale=fontscale
        self.bounding_box=bounding_box
        self.height = height
        self.margin_above=margin_above

        if self.style=="Ideogram":
            if cytobands_file is None or cytobands_file=="":
                if self.reference in ["hg19","hg38"]:
                    with resources.as_file(resources.files(figeno.data) / (self.reference+"_cytobands.tsv")) as infile:
                        self.df_cytobands = pd.read_csv(infile,sep="\t",header=None)
                else:
                    raise Exception("Must provide a cytobands file.")
            else:
                self.df_cytobands = pd.read_csv(self.cytobands_file,sep="\t",header=None)
            self.df_cytobands.columns = ["chr","start","end","value1","value2"]
            self.df_cytobands["chr"] = [x.lstrip("chr") for x in self.df_cytobands["chr"]]

    def draw(self, regions, box ,hmargin):
        boxes = split_box(box,regions,hmargin)
        self.scale=1000
        for i in range(len(regions)):
            
            self.scale = max(self.scale,estimate_scale(boxes[i],regions[i][0]))


        for i in range(len(regions)):
            if "projection" in box and box["projection"]=="polar":
                self.draw_region_circos(regions[i][0],boxes[i])
            elif self.style=="Default" or self.style=="default":
                self.draw_region(regions[i][0],boxes[i]) 
            elif self.style=="Ideogram":
                self.draw_region_ideogram(regions[i][0],boxes[i]) 
            else:
                self.draw_region_arrow(regions[i][0],boxes[i])

    def draw_region(self,region,box):
        if self.bounding_box: draw_bounding_box(box)
        tick_width = 0.3
        #tick_height = (box["top"]-box["bottom"]) * 0.2
        tick_height = 1.6
        #y = box["top"] - tick_height/2 
        if self.ticks_pos=="below" and (not "upside_down" in box):
            if self.no_margin: y=box["top"]
            else: y = box["top"] - tick_height/2
        else:
            if self.no_margin: y=box["bottom"]
            else: y = box["bottom"] + tick_height/2

        if not self.no_margin:
            box["ax"].add_patch(patches.Rectangle((box["left"],y-0.7/2),width=box["right"]-box["left"],height=0.7,lw=0,color="#000000"))
            #box["ax"].plot([box["left"],box["right"]],[y,y],linewidth=2,color="black")

        #ticks
        if self.scale < 1.2 * 1e8:

            # First identify the rightmost tick
            rightmost_tick=0
            for x in range((region.end-region.start)//self.scale +2):
                pos = self.scale * (region.start//self.scale + x)
                if pos<region.start or pos>region.end: continue
                # x 
                if region.orientation=="+":
                    pos_transformed = box["left"] + (pos-region.start) / (region.end-region.start) *(box["right"]-box["left"])
                else:
                    pos_transformed = box["right"] - (pos-region.start) / (region.end-region.start) *(box["right"]-box["left"])
                rightmost_tick  = max(rightmost_tick,pos_transformed)
            # Then, actually draw the tick
            for x in range((region.end-region.start)//self.scale +2):
                pos = self.scale * (region.start//self.scale + x)
                if pos<region.start or pos>region.end: continue

                # x 
                if region.orientation=="+":
                    pos_transformed = box["left"] + (pos-region.start) / (region.end-region.start) *(box["right"]-box["left"])
                else:
                    pos_transformed = box["right"] - (pos-region.start) / (region.end-region.start) *(box["right"]-box["left"])

                # y
                if not self.no_margin:
                    rect = patches.Rectangle((pos_transformed-tick_width/2,y-tick_height/2),tick_width, tick_height,color="black",lw=0)  
                else:
                    if self.ticks_pos=="below" and (not "upside_down" in box):
                        rect = patches.Rectangle((pos_transformed-tick_width/2,y-tick_height/2),tick_width, tick_height/2,color="black",lw=0)  
                    else:
                        rect = patches.Rectangle((pos_transformed-tick_width/2,y),tick_width, tick_height/2,color="black",lw=0)  
                box["ax"].add_patch(rect)

                # x ticks
                #box["ax"].plot([pos_transformed],[y],marker="|",markersize=100,color="black")
                
                if abs(pos_transformed-box["left"])<5: 
                    halign="left"
                    pos_transformed = box["left"]
                elif abs(pos_transformed-box["right"])<5: 
                    halign="right"
                    pos_transformed=box["right"]
                else: halign="center"
                if self.ticks_pos=="below" and (not "upside_down" in box):
                    box["ax"].text(pos_transformed,y-tick_height*0.7,self.tick_text(pos,pos_transformed==rightmost_tick),horizontalalignment=halign,verticalalignment="top",fontsize=7*self.fontscale)
                else:
                    box["ax"].text(pos_transformed,y+tick_height*0.7,self.tick_text(pos,pos_transformed==rightmost_tick),horizontalalignment=halign,verticalalignment="bottom",fontsize=7*self.fontscale)
        # Chr label
        if self.ticks_pos=="below" and (not "upside_down" in box):
            box["ax"].text((box["left"]+box["right"])/2,box["bottom"],"chr"+region.chr,horizontalalignment="center",verticalalignment="bottom",fontsize=9*self.fontscale)
        else:
            box["ax"].text((box["left"]+box["right"])/2,box["top"],"chr"+region.chr,horizontalalignment="center",verticalalignment="top",fontsize=9*self.fontscale)
    
    def draw_region_arrow(self,region,box):
        arrow_height = (box["top"]-box['bottom']) * 0.5
        line_height = arrow_height*0.5
        arrow_width = arrow_height
        if self.ticks_pos=="below" and (not "upside_down" in box):
            h1=box["top"]-arrow_height/2+line_height/2
        else:
            h1=box["bottom"]+arrow_height/2+line_height/2
        if region.orientation=="+":
            polygon_vertices = [(box["left"],h1) , (box["right"]-arrow_width,h1),(box["right"]-arrow_width,h1+arrow_height/2-line_height/2),
                                (box["right"], h1-line_height/2) , (box["right"]-arrow_width,h1-line_height/2-arrow_height/2), 
                                (box["right"]-arrow_width,h1-line_height) , (box["left"],h1-line_height)]
        else:
            polygon_vertices = [ (box["right"],h1) , (box["left"]+arrow_width,h1) , (box["left"]+arrow_width,h1+arrow_height/2-line_height/2),
                                 (box["left"], h1-line_height/2) , (box["left"] +arrow_width,h1-line_height/2-arrow_height/2),
                                 (box["left"] + arrow_width,h1-line_height) , (box["right"],h1-line_height)]
        polygon = patches.Polygon(polygon_vertices,lw=0.0,color=region.color)
        box["ax"].add_patch(polygon)

        if self.ticks_pos=="below" and (not "upside_down" in box):
            ytext=box["top"]-arrow_height*1.2
            valign = "top"
        else:
            ytext=box["bottom"]+arrow_height*1.2
            valign="bottom"

        if region.orientation=="+":
            box["ax"].text(box["left"],ytext,self.tick_text(region.start),horizontalalignment="left",verticalalignment=valign,
                           fontsize=8*self.fontscale)
            box["ax"].text(box["right"],ytext,self.tick_text(region.end),horizontalalignment="right",verticalalignment=valign,
                           fontsize=8*self.fontscale)
        else:
            box["ax"].text(box["left"],ytext,self.tick_text(region.end),horizontalalignment="left",verticalalignment=valign,
                           fontsize=8*self.fontscale)
            box["ax"].text(box["right"],ytext,self.tick_text(region.start),horizontalalignment="right",verticalalignment=valign,
                           fontsize=8*self.fontscale)

        if self.ticks_pos=="below" and (not "upside_down" in box):
            box["ax"].text((box["right"]+box["left"])/2,box["top"]-arrow_height*1.5,"chr"+region.chr.lstrip("chr"),horizontalalignment="center",verticalalignment="top",
                           fontsize=10*self.fontscale)
        else:
            box["ax"].text((box["right"]+box["left"])/2,box["bottom"]+arrow_height*1.5,"chr"+region.chr.lstrip("chr"),horizontalalignment="center",verticalalignment="bottom",
                           fontsize=10*self.fontscale)
            
    def draw_region_ideogram(self,region,box):
        height = (box["top"]-box["bottom"]) * 0.5
        if self.ticks_pos=="below" and (not "upside_down" in box):
            y = box["bottom"] + (box["top"]-box["bottom"]) * 0.75
            if self.fontscale>0:
                box["ax"].text((box["left"]+box["right"])/2, box["top"]-height-1, "chr"+region.chr,
                           horizontalalignment="center", verticalalignment="top",fontsize=10*self.fontscale)
        elif self.ticks_pos=="above":
            y = box["bottom"] + (box["top"]-box["bottom"]) * 0.25
            if self.fontscale>0:
                box["ax"].text((box["left"]+box["right"])/2, box["bottom"] + height+1, "chr"+region.chr,
                           horizontalalignment="center", verticalalignment="bottom",fontsize=10*self.fontscale)
        else:
            y= (box["bottom"]+box["top"]) / 2

        df_cytobands_chr = self.df_cytobands.loc[self.df_cytobands["chr"]==region.chr,:].reset_index(drop=True)
        for i in df_cytobands_chr.index:
            start,end = df_cytobands_chr.loc[i,"start"],df_cytobands_chr.loc[i,"end"]
            # Color based on cytoband
            if df_cytobands_chr.loc[i,"value2"] in ["gneg"]:
                color_coef = 1.0
            elif df_cytobands_chr.loc[i,"value2"] in ["gpos25"]:
                color_coef = 0.8
            elif df_cytobands_chr.loc[i,"value2"] in ["gpos50","stalk"]:
                color_coef = 0.6
            elif df_cytobands_chr.loc[i,"value2"] in ["gpos75"]:
                color_coef = 0.4
            elif df_cytobands_chr.loc[i,"value2"] in ["gpos100","gvar","acen"]:
                color_coef = 0.2
            else:
                print("Unrecognized cytoband value: "+ df_cytobands_chr.loc[i,"value2"])
            color_adjusted = change_color(region.color,color_coef=color_coef)

            if region.orientation=="+":
                x_start = box["left"] + (box["right"]-box["left"]) * (start-region.start)/(region.end-region.start)
                x_end = box["left"] + (box["right"]-box["left"]) * (end-region.start)/(region.end-region.start)
            else:
                x_start = box["right"] - (box["right"]-box["left"]) * (start-region.start)/(region.end-region.start)
                x_end = box["right"] - (box["right"]-box["left"]) * (end-region.start)/(region.end-region.start)
            
            # Rectangle for most cytobands, and half-ellipses for telomeres and centromeres.
            if (i==0  and region.orientation=="+") or (i==df_cytobands_chr.shape[0]-1 and region.orientation=="-"): # Telomere 1
                patch= patches.Ellipse((x_end,y),2*(x_end-x_start),height,facecolor=color_adjusted,edgecolor="black",lw=0.2,fill=True,zorder=-1)
                box["ax"].add_patch(patch)
            elif (i==df_cytobands_chr.shape[0]-1 and region.orientation=="+") or (i==0 and region.orientation=="-"): # Telomere 2
                if (end-start)>12000000:
                    if region.orientation=="+":x_mid = box["left"] + (box["right"]-box["left"]) * (end-10000000-region.start)/(region.end-region.start)
                    else:x_mid = box["right"] - (box["right"]-box["left"]) * (start+10000000-region.start)/(region.end-region.start)
                    vertices = [(x_start,y-height/2) , (x_start, y+height/2) , (x_mid,y+height/2) , (x_mid,y-height/2)]
                    rect = patches.Polygon(vertices,facecolor=color_adjusted,edgecolor="black",lw=0.2)
                    box["ax"].add_patch(rect)
                    patch= patches.Ellipse((x_mid,y),2*(x_end-x_mid),height,facecolor=color_adjusted,edgecolor="black",lw=0.2,fill=True,zorder=-1)
                else:
                    patch= patches.Ellipse((x_start,y),2*(x_end-x_start),height,facecolor=color_adjusted,edgecolor="black",lw=0.2,fill=True,zorder=-1)
                box["ax"].add_patch(patch)
            elif df_cytobands_chr.loc[i,"value2"]=="acen":
                if (df_cytobands_chr.loc[i,"value1"].startswith("p") and region.orientation=="+") or (df_cytobands_chr.loc[i,"value1"].startswith("q") and region.orientation=="-"): # Centromere 1
                    patch= patches.Ellipse((x_start,y),2*(x_end-x_start),height,facecolor=color_adjusted,edgecolor="black",lw=0.2,fill=True,zorder=-1)
                    box["ax"].add_patch(patch)
                else: # Centromere 2
                    patch= patches.Ellipse((x_end,y),2*(x_end-x_start),height,facecolor=color_adjusted,edgecolor="black",lw=0.2,fill=True,zorder=-1)
                    box["ax"].add_patch(patch)
            else:
                vertices = [(x_start,y-height/2) , (x_start, y+height/2) , (x_end,y+height/2) , (x_end,y-height/2)]
                rect = patches.Polygon(vertices,facecolor=color_adjusted,edgecolor="black",lw=0.2)
                box["ax"].add_patch(rect)
        
    def tick_text(self,pos,show_unit=True):
        if self.unit=="kb": 
            if show_unit:
                return f"{pos//1000:,}kb"
            else:
                return f"{pos//1000:,}"
        elif self.unit=="Mb":
            if show_unit:
                if self.scale>1000000: return f"{pos//1000000:,}Mb"
                else: return f"{(pos//100000)/10:,}Mb"
            else:
                if self.scale>1000000: return f"{pos//1000000:,}"
                else: return f"{(pos//100000)/10:,}"
        else:  return f"{pos:,}"

    def draw_region_circos(self,region,box):
        r_rec = (box["bottom"]+box["top"])/2
        if abs(box["right"]-box["left"]) > 0.5:
            arrow_angle=0.07
        else:
            arrow_angle=0.03
        r1=box["bottom"]
        r2 = box["bottom"] + (box["top"] - box["bottom"]) *0.15
        r3 = box["bottom"] + (box["top"] - box["bottom"]) *0.45
        r4 = box["bottom"] + (box["top"] - box["bottom"]) *0.6
        polygon_vertices = [(box["left"],box["bottom"]) , (box["left"],r_rec) , (box["right"] ,r_rec) , (box["right"],box["bottom"])]
        polygon_vertices = interpolate_polar_vertices(polygon_vertices)

        polygon_vertices = [(box["left"],r2) , (box["left"],r3) , (box["right"]+arrow_angle ,r3) , (box["right"]+arrow_angle,r4),
                            (box["right"],(r2+r3)/2) , (box["right"]+arrow_angle,r1) , (box["right"]+arrow_angle,r2)]
        polygon_vertices = interpolate_polar_vertices(polygon_vertices)

        polygon = patches.Polygon(polygon_vertices,lw=0.0,color=region.color)
        box["ax"].add_patch(polygon)

        # label the region (need to rotate the text)
        rotation_text,halign,valign = compute_rotation_text((box["left"]+box["right"])/2)

        r_text = r_rec+(box["top"]-box["bottom"])*0.1

        box["ax"].text((box["left"]+box["right"])/2,r_text,region.chr,rotation=rotation_text,verticalalignment=valign,horizontalalignment=halign,fontsize=22*self.fontscale)

        #,bbox=dict(facecolor='red', alpha=0.4, edgecolor='black')

    def get_highlights_offsets(self):
        # Adjust highlight box depending on the chr axis
        if self.no_margin:
            return (0,0)

        if self.style=="Default":
            if self.ticks_pos=="below":
                return (0,self.height-0.5)
            else:
                return (-self.height+0.5,0)
        else:
            if self.ticks_pos=="below":
                return (0,self.height *7/8)
            else:
                return (-7/8*self.height,0)
                



def estimate_scale(box,region):
    scale = 1000
    while (region.end-region.start)/scale  / (box["right"] - box["left"]) > 1/4: 
        scale*=10
    if (region.end-region.start)/scale / (box["right"] - box["left"]) > 1/4 / 2:
        scale*=5
    elif (region.end-region.start)/scale / (box["right"] - box["left"]) > 1/4 / 4:
        scale*=2
    
    return scale

def color2rgb(c):
    if c in mcolors.get_named_colors_mapping():
        c = mcolors.get_named_colors_mapping()[c]
    # Assume c is now a hex value
    return mcolors.hex2color(c)

def change_color(c,color_coef):
    c = color2rgb(c)
    return (c[0]*color_coef,c[1]*color_coef,c[2]*color_coef)
    #hsv = colorsys.rgb_to_hls(*color2rgb(c))
    #hsv = (hsv[0],hsv[1],color_coef*hsv[2])
    #return colorsys.hsv_to_rgb(*hsv)