# v0.2.3

## 한국어

v0.2.3은 날짜가 바뀌는 즉시 새 예보를 요청하고, Weatheri 게시가 늦을 때 5분, 15분, 30분 간격으로 다시 확인합니다. 어제 예보는 오늘 자료로 재사용하지 않으며, 진단 엔터티에서 재시도 횟수를 확인할 수 있습니다. 기존 설정과 엔터티 ID는 그대로 유지됩니다. Home Assistant 2026.3.0 이상이 필요하며 Weatheri 자료의 개인적·비상업적 이용 제한은 그대로 적용됩니다.

## English

v0.2.3 requests the new forecast immediately at the local date boundary and retries after 5, 15, and 30 minutes when Weatheri publishes late. Yesterday's forecast is never reused as today's data, and the diagnostic entity reports the rollover retry count. Existing configuration and entity IDs are preserved. Home Assistant 2026.3.0 or newer is required, and Weatheri data remains limited to personal, non-commercial use.
