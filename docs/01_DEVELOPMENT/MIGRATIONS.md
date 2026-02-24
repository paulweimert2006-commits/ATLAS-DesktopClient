# Datenbank-Migrationen

> **Stand**: 24.02.2026 | **Gesamt**: 19 Migrationen
> **Pfad**: `BiPro-Webspace Spiegelung Live/setup/`
> **Ausfuehrung**: Manuell via Browser oder CLI auf dem Server

---

## Migrations-Verzeichnis

| ID | Datei | Feature-Version | Tabellen betroffen | Beschreibung | Rollback |
|----|-------|-----------------|-------------------|--------------|----------|
| 005 | `005_add_box_columns.php` | v0.8.0 | `documents` | Box-System Spalten (`box_type`, `processing_status`, `source_type`) | Ja (ALTER DROP) |
| 006 | `006_add_bipro_category.php` | v0.9.0 | `documents` | BiPRO-Kategorie Spalte (`bipro_category_code`, `bipro_category_name`) | Ja (ALTER DROP) |
| 007 | `007_add_is_archived.php` | v0.9.0 | `documents` | Archivierungs-Flag (`is_archived`) | Ja (ALTER DROP) |
| 008 | `008_add_box_type_falsch.php` | v0.9.0 | `documents` | Box-Type Korrektur (ENUM-Erweiterung) | Nein |
| 010 | `010_smartscan_email.php` | v1.0.6 | `email_accounts`, `smartscan_settings`, `smartscan_jobs`, `smartscan_job_items`, `smartscan_emails`, `email_inbox`, `email_inbox_attachments` | E-Mail-System (SMTP/IMAP, SmartScan, Inbox) | Ja (DROP TABLE) |
| 011 | `011_fix_smartscan_schema.php` | v1.0.6 | `smartscan_*`, `email_*` | Schema-Korrekturen E-Mail-System | Nein |
| 012 | `012_add_documents_history_permission.php` | v1.1.2 | `permissions`, `user_permissions` | Neue Berechtigung `documents_history` | Ja (DELETE) |
| 013 | `013_rate_limits.php` | v1.1.0 | - | Rate-Limiting Tabelle | Ja (DROP TABLE) |
| 014 | `014_encrypt_passwords.php` | v1.0.5 | `known_passwords` | Passwort-Tabelle (PDF/ZIP-Passwoerter) | Ja (DROP TABLE) |
| 015 | `015_message_center.php` | v2.0.0 | `messages`, `message_reads`, `private_conversations`, `private_messages` | Mitteilungszentrale + 1:1 Chat | Ja (DROP TABLE) |
| 016 | `016_empty_page_detection.php` | v2.0.2 | `documents` | Leere-Seiten-Spalten (`empty_page_count`, `total_page_count`) | Ja (ALTER DROP) |
| 017 | `017_document_ai_data.php` | v2.0.2 | `document_ai_data` | Volltext + KI-Daten (separates 1:1-Table, CASCADE DELETE) | Ja (DROP TABLE) |
| 018 | `018_content_duplicate_detection.php` | v2.0.3 | `documents` | Content-Duplikat-Spalte (`content_duplicate_of_id`) + Backfill | Ja (ALTER DROP) |
| 024 | `024_provision_matching_v2.php` | v3.2.0 | `pm_commissions`, `pm_contracts` | VN-Normalisierung, 11 Indizes, UNIQUE Constraints, Backfill | Teilweise |
| 025 | `025_provision_indexes.php` | v3.2.1 | `pm_commissions`, `pm_contracts`, `pm_berater_abrechnungen` | 8 operative Indizes + UNIQUE Constraint | Ja (DROP INDEX) |
| 026 | `026_vsnr_renormalize.php` | v3.2.2 | `pm_commissions`, `pm_contracts` | Re-Normalisierung VSNRs (alle Nullen entfernen) | Nein (Daten-Migration) |
| 027 | `027_reset_provision_data.php` | v3.2.2 | `pm_commissions`, `pm_contracts`, `pm_import_batches`, `pm_berater_abrechnungen` | Gefahrenzone: Daten-Reset (behaelt Employees/Models/Mappings) | Nein (destruktiv) |
| 028 | `028_xempus_complete.php` | v3.3.0 | `xempus_*` (6 Tabellen) | Xempus Insight Engine (Snapshots, Beratungen, Arbeitnehmer, Arbeitgeber, Versorgungen, Meta) | Ja (DROP TABLE) |
| 029 | `029_provision_role_permissions.php` | v3.3.0 | `permissions`, `user_permissions` | `provision_access` + `provision_manage` Berechtigungen + Admin-Zuweisung | Ja (DELETE) |

---

## Hinweise

### Luecken in der Nummerierung
- IDs 001-004: Initial-Setup (vor Git, nicht versioniert)
- ID 009: `known_passwords` Initial-Setup (vor Migration 014 zusammengefuehrt)
- IDs 019-023: `processing_ai_settings`, `ai_provider_keys`, `model_pricing`, `ai_requests`, `document_rules_settings` (Inline-Migrations in PHP-Dateien)

### Ausfuehrungsreihenfolge
- Migrationen muessen in aufsteigender ID-Reihenfolge ausgefuehrt werden
- Jede Migration ist idempotent (prueft ob Aenderung bereits angewendet)
- **Nach Ausfuehrung**: Migrations-Datei aus `setup/` loeschen (wird sonst erneut synchronisiert)

### FULLTEXT-Indizes
- `document_ai_data.extracted_text` hat FULLTEXT-Index (MySQL InnoDB)
- Wird fuer ATLAS Index Volltextsuche verwendet (`MATCH ... AGAINST` in BOOLEAN MODE)

### CASCADE-Regeln
- `document_ai_data` → CASCADE DELETE bei Dokument-Loeschung (DSGVO)
- `pm_commissions.contract_id` → SET NULL bei Vertrags-Loeschung
