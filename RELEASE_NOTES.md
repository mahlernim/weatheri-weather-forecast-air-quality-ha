# v0.2.1

## 한국어

v0.2.1은 공개 저장소 배포를 위한 패치 릴리스입니다. 개인적·비상업적 이용과 원자료 재배포 제한을 명확히 안내하고, HACS 메타데이터와 사용자 문서를 정리했습니다. 통합 구성요소의 데이터 처리 동작은 v0.2.0과 같습니다.

## English

v0.2.1 is a public-repository readiness patch. It clarifies personal, non-commercial use and source-data redistribution restrictions, and completes HACS metadata while simplifying user documentation. Integration data behavior is unchanged from v0.2.0.

# v0.2.0

## 한국어

v0.2.0은 URL 입력을 전국 지역·측정소 선택 방식으로 바꾸고 대기정보를 추가합니다. v0.1 설정은 자동으로 이전되며 처음에는 예보만 사용합니다. 독립된 예보/대기 갱신, 3시간 대기 캐시, 간소화한 진단 속성, 새 브랜드 자산을 포함합니다. 독립 `last_success` 센서는 제거되며 값은 예보 진단 이진 센서의 속성으로 이동합니다. Home Assistant 2026.3.0 이상이 필요합니다.

## English

v0.2.0 replaces pasted URLs with nationwide location/station selection and adds air quality. Version 1 entries migrate automatically in forecast-only mode. It includes independent forecast/air updates, a three-hour air cache, streamlined diagnostic attributes, and original branding. The standalone `last_success` sensor is removed; its value moves to the forecast diagnostic binary sensor. Home Assistant 2026.3.0 or newer is required.
