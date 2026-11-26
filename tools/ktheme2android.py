#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ktheme2android.py  —  iOS 카카오톡 테마 → 안드로이드 테마 소스 변환기 (개인용, 내 PC 실행)

하는 일
  iOS 테마(.ktheme 또는 폴더: KakaoTalkTheme.css + 이미지들)를 넣으면
  어피치 안드로이드 템플릿에 끼워서 "빌드 직전까지 완성된 소스 트리"를 만들어 줌.
    - 색상  : css → theme/values/colors.xml  (color+alpha → #AARRGGBB 자동 합침)
    - 이미지 : iOS png → 안드로이드 파일명으로 복사 (theme/drawable-xxhdpi/)
    - 말풍선 : 평면 png + cap인셋 → 나인패치(.9.png) 자동 생성
  나머지(빌드/서명)는 내 PC에서:  cd <출력폴더> && ./gradlew assembleDebug

사용법
  pip install Pillow
  python3 ktheme2android.py --ios  내테마.ktheme \
                           --template apeach-26_1_0-source.zip \
                           --out  build_my_theme

  --scale 3 : iOS 이미지가 @3x 기준이면 3 (기본). @2x뿐이면 2.

★ 카톡 버전 바뀌어 리소스 이름이 달라지면 아래 COLOR_RULES / IMAGE_RULES 두 표만 수정.
"""

import re, sys, os, json, shutil, zipfile, tempfile, argparse
from PIL import Image

# ════════════════════════════════════════════════════════════════
#  매핑표 (여기만 손대면 됨)
# ════════════════════════════════════════════════════════════════
COLOR_RULES = {
 "theme_header_color":("map","HeaderStyle-Main","-ios-text-color",None),
 "theme_section_title_color":("map","SectionTitleStyle-Main","-ios-text-color",None),
 "theme_title_color":("map","MainViewStyle-Primary","-ios-text-color",None),
 "theme_title_pressed_color":("map","MainViewStyle-Primary","-ios-highlighted-text-color",None),
 "theme_paragraph_color":("map","MainViewStyle-Primary","-ios-paragraph-text-color",None),
 "theme_paragraph_pressed_color":("map","MainViewStyle-Primary","-ios-paragraph-highlighted-text-color",None),
 "theme_description_color":("map","MainViewStyle-Primary","-ios-description-text-color",None),
 "theme_description_pressed_color":("map","MainViewStyle-Primary","-ios-description-highlighted-text-color",None),
 "theme_feature_primary_color":("map","FeatureStyle-Primary","-ios-text-color",None),
 "theme_feature_primary_pressed_color":("derive","theme_feature_primary_color"),
 "theme_feature_browse_tab_color":("map","HeaderStyle-Main","-ios-tab-text-color",None),
 "theme_feature_browse_tab_focused_color":("map","HeaderStyle-Main","-ios-tab-highlighted-text-color",None),
 "theme_background_color":("map","MainViewStyle-Primary","background-color",None),
 "theme_chatroom_background_color":("map","BackgroundStyle-ChatRoom","background-color",None),
 "theme_passcode_background_color":("map","BackgroundStyle-Passcode","background-color",None),
 "theme_header_cell_color":("map","MainViewStyle-Primary","background-color",None),
 "theme_body_cell_color":("map","MainViewStyle-Primary","-ios-normal-background-color","-ios-normal-background-alpha"),
 "theme_body_cell_pressed_color":("map","MainViewStyle-Primary","-ios-selected-background-color","-ios-selected-background-alpha"),
 "theme_body_cell_border_color":("map","SectionTitleStyle-Main","border-color","border-alpha"),
 "theme_body_secondary_cell_color":("map","MainViewStyle-Secondary","background-color",None),
 "theme_maintab_cell_color":("default","#00FFFFFF"),
 "theme_tab_lightbannerbadge_background_color":("map","BottomBannerStyle-Light","background-color",None),
 "theme_tab_bannerbadge_background_color":("map","BottomBannerStyle","background-color",None),
 "theme_direct_share_color":("map","LabelStyle-DirectShareBarName","-ios-text-color",None),
 "theme_direct_share_button_color":("derive","theme_direct_share_color"),
 "theme_direct_share_background_color":("map","BackgroundStyle-DirectShareBar","background-color",None),
 "theme_notification_color":("map","LabelStyle-MessageNotificationBarName","-ios-text-color",None),
 "theme_notification_background_color":("map","BackgroundStyle-MessageNotificationBar","background-color",None),
 "theme_notification_background_pressed_color":("derive","theme_notification_background_color"),
 "theme_passcode_color":("map","LabelStyle-PasscodeTitle","-ios-text-color",None),
 "theme_passcode_keypad_color":("map","PasscodeStyle","-ios-keypad-text-normal-color",None),
 "theme_passcode_keypad_pressed_color":("derive","theme_passcode_keypad_color"),
 "theme_passcode_keypad_background_color":("map","PasscodeStyle","-ios-keypad-background-color",None),
 "theme_passcode_keypad_pressed_background_color":("derive","theme_passcode_keypad_background_color"),
 "theme_passcode_pattern_line_color":("map","LabelStyle-PasscodeTitle","-ios-text-color",None),
 "theme_chatroom_bubble_me_color":("map","MessageCellStyle-Send","-ios-text-color",None),
 "theme_chatroom_bubble_you_color":("map","MessageCellStyle-Receive","-ios-text-color",None),
 "theme_chatroom_unread_count_color":("map","MessageCellStyle-Send","-ios-unread-text-color",None),
 "theme_chatroom_input_bar_color":("map","InputBarStyle-Chat","-ios-button-text-color",None),
 "theme_chatroom_input_bar_background_color":("map","InputBarStyle-Chat","background-color",None),
 "theme_chatroom_input_bar_menu_icon_color":("map","InputBarStyle-Chat","-ios-button-normal-foreground-color",None),
 "theme_chatroom_input_bar_menu_button_color":("map","InputBarStyle-Chat","-ios-button-normal-background-color","-ios-button-normal-background-alpha"),
 "theme_chatroom_input_bar_send_icon_color":("map","InputBarStyle-Chat","-ios-send-normal-foreground-color",None),
 "theme_chatroom_input_bar_send_button_color":("map","InputBarStyle-Chat","-ios-send-normal-background-color",None),
}

# 안드로이드파일명 → (셀렉터, 속성, 모드)   모드: None=평면복사 / "ninepatch"=말풍선
IMAGE_RULES = {
 "theme_background_image.png":("MainViewStyle-Primary","-ios-background-image",None),
 "theme_chatroom_background_image.png":("BackgroundStyle-ChatRoom","-ios-background-image",None),
 "theme_find_add_friend_button_image.png":("ButtonStyle-AddFriend","-ios-image",None),
 "theme_profile_01_image.png":("DefaultProfileStyle","-ios-profile-images",None),
 "theme_maintab_ico_friends_image.png":("TabBarStyle-Main","-ios-friends-normal-icon-image",None),
 "theme_maintab_ico_friends_focused_image.png":("TabBarStyle-Main","-ios-friends-selected-icon-image",None),
 "theme_maintab_ico_chats_image.png":("TabBarStyle-Main","-ios-chats-normal-icon-image",None),
 "theme_maintab_ico_chats_focused_image.png":("TabBarStyle-Main","-ios-chats-selected-icon-image",None),
 "theme_maintab_ico_shopping_image.png":("TabBarStyle-Main","-ios-shopping-normal-icon-image",None),
 "theme_maintab_ico_shopping_focused_image.png":("TabBarStyle-Main","-ios-shopping-selected-icon-image",None),
 "theme_maintab_ico_more_image.png":("TabBarStyle-Main","-ios-more-normal-icon-image",None),
 "theme_maintab_ico_more_focused_image.png":("TabBarStyle-Main","-ios-more-selected-icon-image",None),
 "theme_maintab_ico_piccoma_image.png":("TabBarStyle-Main","-ios-piccoma-normal-icon-image",None),
 "theme_maintab_ico_piccoma_focused_image.png":("TabBarStyle-Main","-ios-piccoma-selected-icon-image",None),
 "theme_maintab_ico_now_image.png":("TabBarStyle-Main","-ios-now-normal-icon-image",None),
 "theme_maintab_ico_now_focused_image.png":("TabBarStyle-Main","-ios-now-selected-icon-image",None),
 "theme_maintab_ico_call_image.png":("TabBarStyle-Main","-ios-call-normal-icon-image",None),
 "theme_maintab_ico_call_focused_image.png":("TabBarStyle-Main","-ios-call-selected-icon-image",None),
 "theme_passcode_background_image.png":("BackgroundStyle-Passcode","-ios-background-image",None),
 "theme_chatroom_bubble_me_01_image.9.png":("MessageCellStyle-Send","-ios-background-image","ninepatch"),
 "theme_chatroom_bubble_me_02_image.9.png":("MessageCellStyle-Send","-ios-group-background-image","ninepatch"),
 "theme_chatroom_bubble_you_01_image.9.png":("MessageCellStyle-Receive","-ios-background-image","ninepatch"),
 "theme_chatroom_bubble_you_02_image.9.png":("MessageCellStyle-Receive","-ios-group-background-image","ninepatch"),
 "theme_passcode_01_image.png":("PasscodeStyle","-ios-bullet-first-image",None),
 "theme_passcode_02_image.png":("PasscodeStyle","-ios-bullet-second-image",None),
 "theme_passcode_03_image.png":("PasscodeStyle","-ios-bullet-third-image",None),
 "theme_passcode_04_image.png":("PasscodeStyle","-ios-bullet-fourth-image",None),
 "theme_passcode_01_checked_image.png":("PasscodeStyle","-ios-bullet-selected-first-image",None),
 "theme_passcode_02_checked_image.png":("PasscodeStyle","-ios-bullet-selected-second-image",None),
 "theme_passcode_03_checked_image.png":("PasscodeStyle","-ios-bullet-selected-third-image",None),
 "theme_passcode_04_checked_image.png":("PasscodeStyle","-ios-bullet-selected-fourth-image",None),
}

# 템플릿 내 경로 (어피치 v26 기준)
TPL_COLORS = "src/main/theme/values/colors.xml"
TPL_DRAWABLE = "src/main/theme/drawable-xxhdpi"

ANDROID_ONLY = [
 "theme_splash_image.png  (스플래시 — iOS엔 없음, 직접 넣기)",
 "theme_maintab_cell_image.9.png  (탭 셀 — 대응 없음)",
 "theme_find_add_friend_button_pressed_image.png  (눌림 — iOS엔 1장뿐, 기본 이미지 재사용 권장)",
]

# ════════════════════════════════════════════════════════════════
#  파서 / 색상 헬퍼
# ════════════════════════════════════════════════════════════════
def parse_css(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    out = {}
    for m in re.finditer(r'([\w\-]+)\s*\{([^}]*)\}', text):
        props = {}
        for line in m.group(2).split(';'):
            if ':' in line:
                k, v = line.split(':', 1)
                props[k.strip()] = v.strip()
        out[m.group(1)] = props
    return out

def norm_hex(v):
    if not v: return None
    v = v.strip().strip("'\"").lstrip('#')
    if len(v) == 3: v = ''.join(c*2 for c in v)
    return v.upper() if re.fullmatch(r'[0-9a-fA-F]{6}', v or '') else None

def with_alpha(rgb, alpha):
    if rgb is None: return None
    if alpha is None: return '#'+rgb
    aa = max(0, min(255, round(float(alpha)*255)))
    return '#%02X%s' % (aa, rgb)

def darken(rgb, f=0.85):
    if not rgb: return '000000'
    r,g,b = (int(rgb[i:i+2],16) for i in (0,2,4))
    return '%02X%02X%02X' % tuple(round(c*f) for c in (r,g,b))

def parse_img(raw):
    if not raw: return None, None, None
    fn = re.search(r"'([^']+)'", raw)
    nums = re.findall(r'(\d+)px', raw)
    return (fn.group(1) if fn else None,
            int(nums[0]) if len(nums)>=1 else None,
            int(nums[1]) if len(nums)>=2 else None)

# ════════════════════════════════════════════════════════════════
#  색상 / 이미지 변환
# ════════════════════════════════════════════════════════════════
def build_colors(css):
    colors, rep = {}, []
    for name, rule in COLOR_RULES.items():
        if rule[0] == "map":
            _, sel, prop, aprop = rule
            rgb = norm_hex(css.get(sel, {}).get(prop, ""))
            alpha = css.get(sel, {}).get(aprop) if aprop else None
            val = with_alpha(rgb, alpha)
            if val: colors[name]=val; rep.append(("ok",name,val))
            else:   colors[name]=("#FFFFFFFF" if "background" in name else "#FF191919"); rep.append(("warn",name,"값없음→기본"))
        elif rule[0] == "derive":
            base = colors.get(rule[1], "#FF000000").lstrip('#')[-6:]
            colors[name]='#'+darken(base); rep.append(("derive",name,colors[name]))
        else:
            colors[name]=rule[1]; rep.append(("default",name,rule[1]))
    return colors, rep

def write_colors_xml(colors, path):
    L = ['<?xml version="1.0" encoding="utf-8"?>','<resources>','']
    L += [f'    <color name="{n}">{v}</color>' for n,v in colors.items()]
    L += ['','</resources>']
    open(path,'w',encoding='utf-8').write('\n'.join(L))

def find_image(images_dir, fname, scale):
    """이미지 폴더에서 파일 찾기. 정확명 → @{scale}x → @2x/@3x → 대소문자 무시."""
    base, ext = os.path.splitext(fname)
    base = re.sub(r'@\dx$', '', base)
    cands = [fname, f"{base}@{scale}x{ext}", f"{base}@3x{ext}",
             f"{base}@2x{ext}", f"{base}{ext}"]
    listing = {f.lower(): f for f in os.listdir(images_dir)} if os.path.isdir(images_dir) else {}
    for c in cands:
        for key in (c.lower(), c.lower().replace("maintabico", "maintablco")):  # 흔한 파일명 오타 허용
            if key in listing:
                return os.path.join(images_dir, listing[key])
    return None

def make_ninepatch(src_png, out_png, cap_x, cap_y, scale):
    """평면 png + cap인셋(1x) → .9.png. 가장자리 1px에 늘어남 마커."""
    im = Image.open(src_png).convert("RGBA")
    w, h = im.size
    cx = (cap_x or 10) * scale
    cy = (cap_y or 10) * scale
    cx = max(1, min(cx, w//2 - 1)); cy = max(1, min(cy, h//2 - 1))
    canvas = Image.new("RGBA", (w+2, h+2), (0,0,0,0))
    canvas.paste(im, (1,1))
    px = canvas.load()
    BLACK = (0,0,0,255)
    for x in range(cx, w-cx):            # 위 테두리: 가로 늘어남
        px[x+1, 0] = BLACK
    for y in range(cy, h-cy):            # 왼 테두리: 세로 늘어남
        px[0, y+1] = BLACK
    for x in range(cx, w-cx):            # 아래 테두리: 콘텐츠 가로영역
        px[x+1, h+1] = BLACK
    for y in range(cy, h-cy):            # 오른 테두리: 콘텐츠 세로영역
        px[w+1, y+1] = BLACK
    canvas.save(out_png)

# ════════════════════════════════════════════════════════════════
#  메인
# ════════════════════════════════════════════════════════════════
def resolve_ios(path, workdir):
    """.ktheme(zip) 또는 폴더 → (css_text, images_dir)"""
    if os.path.isdir(path):
        root = path
    else:
        root = os.path.join(workdir, "ios")
        with zipfile.ZipFile(path) as z:   # .ktheme = zip
            z.extractall(root)
    css_path = None
    for dp,_,fs in os.walk(root):
        for f in fs:
            if f.lower() == "kakaotalktheme.css":
                css_path = os.path.join(dp, f)
    if not css_path:
        sys.exit("✗ KakaoTalkTheme.css 를 찾을 수 없음: " + path)
    images_dir = os.path.dirname(css_path)
    if os.path.isdir(os.path.join(images_dir, "Images")):
        images_dir = os.path.join(images_dir, "Images")
    return open(css_path, encoding="utf-8").read(), images_dir

def resolve_template(path, out):
    """템플릿 zip/폴더 → out 으로 복사한 작업 트리 루트 반환"""
    if os.path.exists(out):
        shutil.rmtree(out)
    if os.path.isdir(path):
        shutil.copytree(path, out)
    else:
        with zipfile.ZipFile(path) as z:
            z.extractall(out)
    # 트리 안에서 src/main 위치 탐색
    for dp,_,fs in os.walk(out):
        if dp.replace("\\","/").endswith("src/main"):
            return os.path.dirname(os.path.dirname(dp))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ios", required=True, help=".ktheme 또는 iOS 테마 폴더")
    ap.add_argument("--template", required=True, help="어피치 안드로이드 소스 zip/폴더")
    ap.add_argument("--out", default="build_theme", help="출력 폴더")
    ap.add_argument("--scale", type=int, default=3, help="iOS 이미지 배수 (기본 3)")
    args = ap.parse_args()

    work = tempfile.mkdtemp()
    css_text, images_dir = resolve_ios(args.ios, work)
    css = parse_css(css_text)
    tb = css.get("TabBarStyle-Main", {})           # View(뷰)탭 → 안드 Now탭 연결 (now 없고 view만 있을 때)
    for a, b in [("-ios-now-normal-icon-image", "-ios-view-normal-icon-image"),
                 ("-ios-now-selected-icon-image", "-ios-view-selected-icon-image")]:
        if not tb.get(a) and tb.get(b):
            tb[a] = tb[b]
    man = css.get("ManifestStyle", {})
    print("■ 테마:", man.get("-kakaotalk-theme-name"), "| author:", man.get("-kakaotalk-author-name"))

    root = resolve_template(args.template, args.out)
    drawable = os.path.join(root, TPL_DRAWABLE)
    os.makedirs(drawable, exist_ok=True)

    # 1) 색상
    colors, crep = build_colors(css)
    write_colors_xml(colors, os.path.join(root, TPL_COLORS))
    warn = sum(1 for s,_,_ in crep if s=="warn")
    print(f"■ 색상 {len(colors)}개 → {TPL_COLORS}  (자동보충/파생 {sum(1 for s,_,_ in crep if s in('derive','default'))}, 경고 {warn})")

    # 2) 이미지 + 나인패치
    done, missing, nine = 0, [], 0
    for andfn, (sel, prop, mode) in IMAGE_RULES.items():
        iosfn, cx, cy = parse_img(css.get(sel, {}).get(prop, ""))
        if not iosfn:
            missing.append(andfn); continue
        src = find_image(images_dir, iosfn, args.scale)
        if not src:
            missing.append(f"{andfn}  (iOS: {iosfn} 못찾음)"); continue
        dst = os.path.join(drawable, andfn)
        if mode == "ninepatch":
            make_ninepatch(src, dst, cx, cy, args.scale); nine += 1
        else:
            Image.open(src).convert("RGBA").save(dst)
        done += 1
    print(f"■ 이미지 {done}개 복사 (나인패치 {nine}개 생성) → {TPL_DRAWABLE}/")
    if missing:
        print(f"■ 못 채운 이미지 {len(missing)}개:")
        for m in missing: print("   -", m)
    print("■ 안드로이드 전용(직접 보충):")
    for x in ANDROID_ONLY: print("   -", x)

    json.dump({"colors":dict(colors)}, open(os.path.join(args.out,"_convert_report.json"),"w",encoding="utf-8"),
              ensure_ascii=False, indent=2)
    shutil.rmtree(work, ignore_errors=True)

    print(f"\n✓ 완료 → '{args.out}'")
    print(f"  다음: cd {args.out} && ./gradlew assembleDebug")
    print(f"  결과 APK: app/build/outputs/apk/debug/*.apk  (폰에 설치 → 카톡 테마 적용)")

if __name__ == "__main__":
    main()
