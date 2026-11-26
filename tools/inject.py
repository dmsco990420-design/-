#!/usr/bin/env python3
# theme_input/(KakaoTalkTheme.css + 이미지) → src/main/theme/ 에 색·이미지 주입
import os, sys
HERE=os.path.dirname(os.path.abspath(__file__)); REPO=os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ktheme2android as K
from PIL import Image

ios=os.path.join(REPO,"theme_input")
scale=int(os.environ.get("SCALE","3"))

# theme_input 에 css 있나?
has_css=any(f.lower()=="kakaotalktheme.css" for _,_,fs in os.walk(ios) for f in fs)
if not has_css:
    print("※ theme_input 에 KakaoTalkTheme.css 가 없어요 → 기본 어피치 그대로 빌드합니다.")
    sys.exit(0)

css_text, images_dir = K.resolve_ios(ios, "/tmp/ktwork")
css=K.parse_css(css_text)
tb=css.get("TabBarStyle-Main",{})
for a,b in [("-ios-now-normal-icon-image","-ios-view-normal-icon-image"),
            ("-ios-now-selected-icon-image","-ios-view-selected-icon-image")]:
    if not tb.get(a) and tb.get(b): tb[a]=tb[b]

res=K.build_colors(css); colors=res[0] if isinstance(res,tuple) else res
K.write_colors_xml(colors, os.path.join(REPO,"src/main/theme/values/colors.xml"))
print("■ 색상", len(colors), "개 주입")

draw=os.path.join(REPO,"src/main/theme/drawable-xxhdpi"); os.makedirs(draw,exist_ok=True)
done=nine=0; miss=[]
for andfn,(sel,prop,mode) in K.IMAGE_RULES.items():
    iosfn,cx,cy=K.parse_img(css.get(sel,{}).get(prop,""))
    if not iosfn: miss.append(andfn); continue
    src=K.find_image(images_dir, iosfn, scale)
    if not src: miss.append(andfn); continue
    dst=os.path.join(draw,andfn)
    if mode=="ninepatch": K.make_ninepatch(src,dst,cx,cy,scale); nine+=1
    else: Image.open(src).convert("RGBA").save(dst)
    done+=1
print(f"■ 이미지 {done}개 주입 (나인패치 {nine}), 누락 {len(miss)}")
print("■ 테마:", css.get("ManifestStyle",{}).get("-kakaotalk-theme-name"))

# ───────── 추가: theme_input/android/ 에 직접 만든 안드로이드 전용 파일이 있으면 덮어쓰기 ─────────
#  android/drawable-xxhdpi/*.png, *.9.png  → src/main/theme/drawable-xxhdpi/  (말풍선 나인패치·스플래시 등)
#  android/mipmap-*/ic_launcher*.png        → src/main/res/mipmap-*/         (앱 아이콘)
#  android/ic_launcher-web.png              → src/main/ic_launcher-web.png
#  android/app.json {"app_name":..,"app_name_ko":..,"application_id":..}  → 앱 이름·앱 ID
import json, re, shutil
AND=os.path.join(ios,"android")
if os.path.isdir(AND):
    n=0
    for dp,_,fs in os.walk(AND):
        rel=os.path.relpath(dp,AND)
        for f in fs:
            if not f.lower().endswith(".png"): continue
            src=os.path.join(dp,f)
            if rel.startswith("drawable"): dst=os.path.join(REPO,"src/main/theme",rel,f)
            elif rel.startswith("mipmap"): dst=os.path.join(REPO,"src/main/res",rel,f)
            elif rel=="." and f=="ic_launcher-web.png": dst=os.path.join(REPO,"src/main",f)
            else: continue
            os.makedirs(os.path.dirname(dst),exist_ok=True); shutil.copyfile(src,dst); n+=1
    print("■ android/ 전용 파일", n, "개 덮어씀")
    cfg=os.path.join(AND,"app.json")
    if os.path.isfile(cfg):
        app=json.load(open(cfg,encoding="utf-8"))
        def strings(name):
            return ('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
                    f'    <string name="theme_title">{name}</string>\n'
                    f'    <string name="app_name">{name}</string>\n</resources>\n')
        for d,key in [("values","app_name"),("values-ko","app_name_ko"),("values-ja","app_name")]:
            p=os.path.join(REPO,"src/main/theme",d,"strings.xml")
            if os.path.isdir(os.path.dirname(p)):
                open(p,"w",encoding="utf-8").write(strings(app.get(key) or app.get("app_name")))
        if app.get("application_id"):
            g=os.path.join(REPO,"build.gradle.kts"); t=open(g,encoding="utf-8").read()
            t=re.sub(r'applicationId\s*=\s*"[^"]*"', f'applicationId = "{app["application_id"]}"', t)
            open(g,"w",encoding="utf-8").write(t)
        if app.get("colors"):
            cp=os.path.join(REPO,"src/main/theme/values/colors.xml"); t=open(cp,encoding="utf-8").read()
            for nm,val in app["colors"].items():
                t=re.sub(r'(<color name="'+nm+r'">)[^<]*(</color>)', r'\g<1>'+val+r'\g<2>', t)
            open(cp,"w",encoding="utf-8").write(t); print("■ 색상 덮어씀:", ", ".join(app["colors"]))
        print("■ 앱 이름:", app.get("app_name_ko"), "/ 앱 ID:", app.get("application_id"))
