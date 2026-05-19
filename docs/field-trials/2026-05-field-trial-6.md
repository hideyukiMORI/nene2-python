# Field Trial 6 — weather: AsyncUseCaseProtocol DX 検証

## Date

2026-05-19

## Baseline

- nene2-python v0.1.0 (`uv add git+https://github.com/hideyukiMORI/nene2-python.git`)
- Python 3.14.5（uv managed）
- プロジェクト: **weather** — 天気ダッシュボード JSON API
- エンティティ: `City`（id, name, latitude, longitude）、`WeatherData`（温度・風速・天気コード）
- 5 エンドポイント: City CRUD + GET /cities/{id}/weather
- 外部 API: **Open-Meteo**（無料・APIキー不要）
- **`AsyncUseCaseProtocol`** ← FT1〜FT5 で未検証のコア機能

## Goal

1. `AsyncUseCaseProtocol` の実用 DX を確認する（`async def execute()` の実装）
2. 同期 UseCase（City CRUD）と非同期 UseCase（weather fetch）の混在パターンを検証する
3. 外部依存（WeatherClientProtocol）をテストで差し替えるパターンを確認する
4. `asyncio_mode = "auto"` による pytest の async テストのDXを確認する

---

## Steps Taken

### 1. プロジェクト初期化・インストール

問題なし。`pyproject.toml` に `pytest-asyncio>=0.24` を追加、`asyncio_mode = "auto"` を設定。

### 2. AsyncUseCaseProtocol を使った GetWeatherUseCase

`async def execute()` を持つ UseCase を実装。同期の City CRUD UseCase と自然に共存：

```python
class GetWeatherUseCase:
    async def execute(self, city_id: int) -> CityWeather:
        city = self._repo.find_by_id(city_id)  # 同期（DB）
        if city is None:
            raise CityNotFoundException(city_id)
        try:
            weather = await self._client.fetch(city.latitude, city.longitude)  # 非同期（外部API）
        except httpx.HTTPError as exc:
            raise WeatherFetchException(str(exc)) from exc
        return CityWeather(city=city, weather=weather)
```

同期リポジトリと非同期クライアントを同一 UseCase 内で混在させることが可能。

### 3. WeatherClientProtocol による依存性の差し替え

```python
class WeatherClientProtocol(Protocol):
    async def fetch(self, latitude: float, longitude: float) -> WeatherData: ...

class FakeWeatherClient:
    async def fetch(self, latitude: float, longitude: float) -> WeatherData:
        return WeatherData(temperature_celsius=20.0, windspeed_kmh=10.0, weathercode=0)
```

Protocol による構造的サブタイピングで、テスト時は FakeWeatherClient を注入するだけ。

### 4. async handler

```python
@router.get("/cities/{city_id}/weather", summary="Get current weather for city")
async def get_weather(city_id: int) -> JSONResponse:
    city_weather = await get_weather_use_case.execute(city_id)
    return JSONResponse({...})
```

FastAPI が `async def` ハンドラーをネイティブサポートするため、追加設定不要。

### 5. pytest async テスト

`asyncio_mode = "auto"` を設定することで、async テスト関数が特別な decorator なしで動作：

```python
async def test_get_weather_returns_city_weather(city_repo, tokyo):
    uc = GetWeatherUseCase(city_repo, FakeWeatherClient())
    result = await uc.execute(tokyo.id)
    assert result.weather.temperature_celsius == 25.0
```

### 6. 実 Open-Meteo API での動作確認

```
POST /cities  {"name": "Tokyo", "latitude": 35.6762, "longitude": 139.6503}
GET  /cities/1/weather
→ {"city": {...}, "weather": {"temperature_celsius": 18.2, "windspeed_kmh": 3.8, "weathercode": 2}}

POST /cities  {"name": "London", "latitude": 51.5074, "longitude": -0.1278}
GET  /cities/2/weather
→ {"city": {...}, "weather": {"temperature_celsius": 16.3, "windspeed_kmh": 23.4, "weathercode": 3}}
```

---

## Friction Points

摩擦ゼロ。すべてのDXが期待通りに動作した。

具体的に確認できた点：
- `AsyncUseCaseProtocol` は structural typing（Protocol）で、`isinstance` チェックが属性存在のみを確認するため、`async def execute` を持つクラスが自然に適合する ✅
- 同期 UseCase（DB）と非同期 UseCase（外部API）の混在は問題なし ✅
- `asyncio_mode = "auto"` で `@pytest.mark.asyncio` が不要 ✅
- FakeWeatherClient で外部 API を完全にモック化できる（ネットワーク不要） ✅
- `pytest-asyncio` の追加が必要（`pyproject.toml` に `asyncio_mode = "auto"` 設定） — 軽微だが初見では非自明

---

## Summary

| ID  | 摩擦 | 深刻度 | 種別 | Follow-up Issue |
|-----|------|--------|------|-----------------|
| なし | — | — | — | — |

FT6 は摩擦ゼロで完走。`AsyncUseCaseProtocol` の DX は期待通り。
`pytest-asyncio` の設定（`asyncio_mode = "auto"`）も自然に馴染む。

次回 FT7 候補：
- **親子リソース（nested REST）**: 例: Blog posts + Comments（GET /posts/{id}/comments）
- **MySQL/PostgreSQL**: SQLite 以外のアダプターを FT で初使用
- **PyPI 公開フロー**: FT6 完了を受けて、いよいよパッケージ公開の DX 検証
