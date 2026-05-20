# TODO — current

最終更新: 2026-05-20
現状: **v1.8.33 安定版 / フィールドトライアルループ継続中**

---

## 状態サマリー

v1.8.33 完了済み。フィールドトライアル FT108/FT109 を含む docs 改善マージ済み。
2026-05-20 時点でオープン PR は PR #428（ResourceWarning 修正）のみ。

---

## オープン PR

| PR | Issue | 内容 |
|---|---|---|
| [#428](https://github.com/hideyukiMORI/nene2-python/pull/428) | #427 | テストの ResourceWarning: unclosed database を解消する |

---

## 直近の完了マイルストーン

| バージョン | 主な追加機能 |
|---|---|
| v1.8.33 | `nene2.cache.TtlCache[V]` |
| v1.8.32 | `nene2.security.verify_hmac_signature()` |
| v1.8.31 | `nene2.http.generate_etag()` |
| v1.8.30 | `problem_details_response()` headers パラメーター |
| v1.8.29 | `make_require_auth()` |
| v1.8.28 | `PaginationDep`, `PaginationResponse.model_dump()` |

---

## フィールドトライアル進捗

**実施済み**: FT1〜FT109（FT108, FT109 含む docs-only）

**次のアクション候補**（優先度順）:
1. ResourceWarning 修正 PR #428 マージ後、バグ修正リリース（v1.8.34）
2. FT110+ — 未検証パターンの探索継続
3. DB 実統合テスト（PostgreSQL/MySQL 実環境）の追加検討
4. PyPI 公開体験の最終確認

---

## 改善検討事項

- 警告ゼロ化: PR #428 でほぼ解消（StaticPool の 1 件は filterwarnings で抑制）
- DB 実統合テスト: SQLite インメモリテストはあるが PostgreSQL/MySQL 実環境テストは未
- PyPI 公開体験の仕上げ: パッケージメタデータ整備済み、公開フロー最終確認が残
