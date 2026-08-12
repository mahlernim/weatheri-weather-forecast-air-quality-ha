# Weatheri Weather & Air

![Weatheri Weather & Air](custom_components/weatheri_forecast/brand/logo.png)

## 한국어

### 개요

Weatheri 지역별 예보의 오늘·내일 최고/최저 기온과 실시간 대기정보를 Home Assistant 센서로 제공합니다. 전국 172개 예보 지역을 검색 가능한 목록에서 선택하고, 해당 권역의 대기 측정소를 추가로 선택할 수 있습니다. 예보만 사용하는 설정도 지원합니다.

이 프로젝트는 비공식 커뮤니티 통합 구성요소입니다. Weatheri 및 한국환경공단이 개발·보증·후원하지 않습니다. 예보 자료의 출처는 Weatheri이며, 대기 관측 자료는 Weatheri 페이지에 표시된 한국환경공단 자료입니다. 원자료의 이용 조건과 서비스 가용성을 존중하십시오.

**데이터 이용 안내:** 이 통합 구성요소는 개인적·비상업적 이용을 위한 것입니다. [Weatheri 이용약관](https://www.weatheri.co.kr/company/company_pop.php)은 서비스 정보를 자신을 위해 사용하는 범위를 벗어나 공개 게시하거나 제3자에게 제공하고, 복제·배포·송신·판매 또는 상업적으로 이용하는 행위를 제한합니다. 이 통합 구성요소는 Weatheri 데이터를 재배포하지 않으며, 각 사용자의 Home Assistant가 선택한 정보를 Weatheri에서 직접 조회합니다. 사용자는 원자료의 이용약관을 준수할 책임이 있습니다.

### 기능

- URL 입력 없이 예보 지역과 대기 측정소를 단계별 목록에서 선택
- 예보와 대기정보를 서로 독립적으로 매시간 갱신하고, 날짜 변경 시 예보를 즉시 재확인
- 오늘/내일 최고·최저 기온과 PM10/PM2.5 기본 제공
- 오존, 이산화질소, 일산화탄소, 아황산가스, 통합대기환경지수 선택 제공
- 예보는 같은 현지 날짜, 대기정보는 관측 시각부터 최대 3시간 동안 캐시 사용

### 설치

Home Assistant 2026.3.0 이상이 필요합니다.

HACS 사용자 지정 저장소:

1. HACS의 **통합 구성요소 → 사용자 지정 저장소**를 엽니다.
2. `https://github.com/mahlernim/weatheri-weather-forecast-air-quality-ha`를 입력하고 유형을 **Integration**으로 지정합니다.
3. **Weatheri Weather & Air**를 설치하고 Home Assistant를 다시 시작합니다.

수동 설치:

1. 최신 GitHub 릴리스의 ZIP 파일을 내려받습니다.
2. `custom_components/weatheri_forecast` 폴더를 Home Assistant의 `/config/custom_components/weatheri_forecast`로 복사합니다.
3. Home Assistant를 다시 시작합니다.

설치 후 **설정 → 기기 및 서비스 → 통합 구성요소 추가 → Weatheri Weather & Air**를 선택합니다. 이 통합 구성요소는 아직 HACS 기본 저장소에 등록되어 있지 않습니다.

### 설정

1. **예보 지역**에서 지역을 검색하여 선택합니다.
2. **대기 측정소**에서 측정소를 선택합니다. 대기정보가 필요하지 않으면 **대기정보 사용 안 함**을 선택합니다.

한 설정 항목은 예보 지역 하나와 선택적인 측정소 하나를 나타냅니다. 동일한 예보 지역은 중복 추가할 수 없습니다.

### 엔터티

| 엔터티 | 기본 상태 | 설명 |
|---|---:|---|
| 오늘/내일 최고·최저 기온 4개 | 사용 | °C 예보 |
| PM10, PM2.5 | 사용 | 선택한 측정소의 ㎍/㎥ 관측값 |
| 오존, 이산화질소, 일산화탄소, 아황산가스, 통합대기환경지수 | 사용 안 함 | 엔터티 설정에서 개별 활성화 가능 |
| 예보 데이터 최신 | 진단 | 날짜, 마지막 성공/시도, 오류 및 캐시 사용 속성 |
| 대기 데이터 최신 | 진단 | 측정소, 관측 시각, 데이터 나이, 누락 항목 및 갱신 상태 |

대기정보를 사용하지 않으면 대기 관련 엔터티를 만들지 않습니다. 별도의 연결 상태나 시각 센서는 만들지 않습니다.

### 캐시와 최신성

예보 갱신이 실패하면 원본 예보 날짜가 Home Assistant 현지 날짜와 같은 동안만 마지막 완전한 자료를 유지합니다. 날짜가 바뀌면 사용할 수 없음으로 전환하고 새 날짜 자료를 즉시 요청합니다. Weatheri 게시가 늦으면 5분, 15분, 30분 간격으로 다시 확인하므로 다음 매시간 갱신까지 기다리지 않습니다. 대기정보는 Weatheri에 게시된 관측 시각부터 3시간 이내이고 PM10과 PM2.5가 모두 있을 때만 최신으로 판단합니다. 개별 `-` 값은 해당 항목만 사용할 수 없음으로 처리합니다.

### 재구성

통합 구성요소의 **구성 → 재구성**에서 대기 측정소를 변경하거나 대기정보를 끌 수 있습니다. 측정소 변경은 대기 엔터티 ID를 변경하지 않습니다. 예보 지역을 변경하려면 기존 항목을 제거하고 새 항목을 추가하십시오.

### 문제 해결

- 설정 목록이 열리지 않으면 Home Assistant에서 `www.weatheri.co.kr`의 HTTPS 연결이 가능한지 확인하십시오.
- 센서가 사용할 수 없음이면 두 진단 이진 센서의 `last_error`, `last_attempt_success`, `data_age_minutes` 속성을 확인하십시오.
- Weatheri HTML 구조가 변경되면 로그에 파싱 오류가 기록될 수 있습니다. 로그와 해당 지역/측정소를 포함하여 이슈를 제출하십시오.
- 로고가 보이지 않으면 Home Assistant 2026.3.0 이상인지 확인하고 브라우저 캐시를 새로 고치십시오.

### 제거

**설정 → 기기 및 서비스**에서 통합 항목을 삭제한 뒤 `/config/custom_components/weatheri_forecast` 폴더를 제거하고 Home Assistant를 다시 시작하십시오.

## English

### Overview

Weatheri Weather & Air exposes today/tomorrow high and low temperatures from Weatheri regional forecasts and monitoring-station air observations as Home Assistant sensors. Select one of 172 nationwide forecast locations from a searchable list, then optionally select a station in its air region. Forecast-only setup is supported.

This is an unofficial community integration. It is not developed, endorsed, sponsored, or supported by Weatheri or the Korea Environment Corporation. Forecast data is attributed to Weatheri; air observations are attributed to the Korea Environment Corporation as displayed by Weatheri. Respect the source services' terms and availability.

**Data-use notice:** This integration is intended for personal, non-commercial use. The [Weatheri Terms of Use](https://www.weatheri.co.kr/company/company_pop.php) restrict publicly posting or providing service information to third parties and prohibit its reproduction, distribution, transmission, sale, or commercial use outside personal use. This integration does not redistribute Weatheri data; each user's Home Assistant retrieves the selected information directly from Weatheri. Users are responsible for complying with the source terms.

### Features

- Guided forecast-location and air-station lists; no pasted URL
- Independent hourly forecast and air updates with an immediate date-boundary refresh
- Today/tomorrow high and low temperatures plus PM10 and PM2.5 by default
- Optional ozone, nitrogen dioxide, carbon monoxide, sulfur dioxide, and comprehensive AQI entities
- Same-local-date forecast cache and air cache limited to three hours from source time

### Installation

Home Assistant 2026.3.0 or newer is required.

HACS custom repository:

1. Open **HACS → Integrations → Custom repositories**.
2. Add `https://github.com/mahlernim/weatheri-weather-forecast-air-quality-ha` with category **Integration**.
3. Install **Weatheri Weather & Air** and restart Home Assistant.

Manual installation:

1. Download the ZIP file from the latest GitHub release.
2. Copy `custom_components/weatheri_forecast` to `/config/custom_components/weatheri_forecast` in Home Assistant.
3. Restart Home Assistant.

After installation, open **Settings → Devices & services → Add integration → Weatheri Weather & Air**. This integration is not yet listed in the HACS default store.

### Setup

1. Search and select a **Forecast location**.
2. Select an **Air-quality station**, or choose **Forecast only**.

One config entry represents one forecast location and at most one station. Duplicate forecast locations are prevented.

### Entities

| Entity | Default | Purpose |
|---|---:|---|
| Four today/tomorrow high/low sensors | Enabled | Forecast in °C |
| PM10 and PM2.5 | Enabled | Selected-station observations in µg/m³ |
| Ozone, nitrogen dioxide, carbon monoxide, sulfur dioxide, comprehensive AQI | Disabled | Individually enable in entity settings |
| Forecast data current | Diagnostic | Source date, last success/attempt, error, and cache attributes |
| Air data current | Diagnostic | Station, source time, age, missing values, and update health |

Air entities are not created for forecast-only entries. Separate reachability and timestamp entities are intentionally omitted.

### Cache and freshness

After a forecast failure, the last complete snapshot remains available only while its source date equals the Home Assistant local date. At the date boundary it expires, requests the new date immediately, and retries after 5, 15, and 30 minutes if Weatheri has not published it yet. Air data is current only when the Weatheri-published observation is no more than three hours old and both PM10 and PM2.5 are present. A `-` affects only that measurement.

### Reconfiguration

Use **Configure → Reconfigure** on the integration entry to change the air station or switch to forecast only. Station changes retain air entity IDs. To change the forecast location, remove the entry and add another one.

### Troubleshooting

- If setup lists do not load, verify HTTPS access from Home Assistant to `www.weatheri.co.kr`.
- If entities are unavailable, inspect `last_error`, `last_attempt_success`, and `data_age_minutes` on the diagnostic binary sensors.
- Weatheri HTML changes may produce parser errors. Include the log, forecast location, and station in an issue.
- If branding is absent, confirm Home Assistant 2026.3.0 or newer and refresh the browser cache.

### Removal

Delete the integration entry under **Settings → Devices & services**, remove `/config/custom_components/weatheri_forecast`, and restart Home Assistant.
