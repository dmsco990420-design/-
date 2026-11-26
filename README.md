# 카톡테마 자동 빌드 (iOS → 안드로이드 APK)

iOS 카카오톡 테마를 올리면 GitHub가 **변환 + 빌드 + 서명**까지 자동으로 해서
**설치 가능한 .apk**를 만들어 줍니다. 내 컴퓨터에 아무것도 설치 안 해도 돼요.

## 처음 한 번 (세팅)

1. github.com 가입 (무료)
2. 오른쪽 위 **＋ → New repository** → 이름 아무거나 → **Create**
3. 만든 repo 화면에서 **uploading an existing file** 클릭 →
   이 폴더의 **모든 파일을 통째로 드래그**해서 올리기 → **Commit changes**

## 테마 만들 때마다

1. repo의 **`theme_input`** 폴더로 들어가기 → **Add file → Upload files**
2. 내 iOS 테마의 **`KakaoTalkTheme.css`** 와 **이미지들(Images 폴더째)** 올리기
3. **Commit changes**
4. 위쪽 **Actions** 탭 클릭 → 방금 빌드가 돌아가요 (5~10분)
5. 초록 체크 ✓ 되면 그 빌드 클릭 → 맨 아래 **Artifacts → kakaotheme-apk** 다운로드
6. 압축 풀면 **kakaotheme.apk** → 폰으로 보내서 설치
   (설치 시 "출처를 알 수 없는 앱 허용" 켜기)

## 참고
- 빌드가 빨간 X로 실패하면, 그 빌드 → 로그를 열어 캡처해서 문의하세요.
- theme_input 을 비워두면 기본 어피치 테마로 빌드됩니다.
