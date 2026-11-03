from PIL import Image, ImageDraw, ImageFont
S=3000
img=Image.new("RGB",(S,S),(18,48,44))
d=ImageDraw.Draw(img)
G="/usr/share/fonts/truetype/sand-box/google/"
reg=G+"EB Garamond/EBGaramond-VariableFont_wght.ttf"
ita=G+"EB Garamond/EBGaramond-Italic-VariableFont_wght.ttf"
gold=(212,180,110); cream=(240,232,210)
def c(y,t,f,fill):
    w=d.textbbox((0,0),t,font=f)[2]; d.text(((S-w)/2,y),t,font=f,fill=fill)
m=150; d.rectangle([m,m,S-m,S-m],outline=gold,width=10); d.rectangle([m+40,m+40,S-m-40,S-m-40],outline=gold,width=3)
big=ImageFont.truetype(reg,330); 
try: big.set_variation_by_name("SemiBold")
except Exception: pass
c(900,"Hashimiya",big,cream); c(1260,"Lectures",big,cream)
d.line([(S/2-350,1720),(S/2+350,1720)],fill=gold,width=6)
c(1800,"in English",ImageFont.truetype(ita,200),gold)
c(2400,"Lessons of the Hashimiyya-Habibiyya path",ImageFont.truetype(ita,95),cream)
c(2520,"Unofficial translations & narrations",ImageFont.truetype(reg,80),(190,190,170))
img.save("cover.png",optimize=True)
