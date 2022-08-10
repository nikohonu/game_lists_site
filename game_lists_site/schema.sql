BEGIN TRANSACTION;
DROP TABLE IF EXISTS "post";
CREATE TABLE IF NOT EXISTS "post" (
	"id"	INTEGER,
	"author_id"	INTEGER NOT NULL,
	"created"	TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	"title"	TEXT NOT NULL,
	"body"	TEXT NOT NULL,
	FOREIGN KEY("author_id") REFERENCES "user"("id"),
	PRIMARY KEY("id" AUTOINCREMENT)
);
DROP TABLE IF EXISTS "steam_app";
CREATE TABLE IF NOT EXISTS "steam_app" (
	"id"	INTEGER,
	"name"	TEXT NOT NULL,
	"is_game"	INTEGER NOT NULL DEFAULT 1,
	PRIMARY KEY("id" AUTOINCREMENT)
);
DROP TABLE IF EXISTS "steam_profile_app";
CREATE TABLE IF NOT EXISTS "steam_profile_app" (
	"steam_profile_id"	INTEGER NOT NULL,
	"steam_app_id"	INTEGER NOT NULL,
	"playtime"	INTEGER NOT NULL,
	FOREIGN KEY("steam_app_id") REFERENCES "steam_app"("id") ON DELETE CASCADE,
	PRIMARY KEY("steam_app_id","steam_profile_id"),
	FOREIGN KEY("steam_profile_id") REFERENCES "steam_profile"("id") ON DELETE CASCADE
);
DROP TABLE IF EXISTS "user";
CREATE TABLE IF NOT EXISTS "user" (
	"id"	INTEGER,
	"username"	TEXT NOT NULL UNIQUE,
	"password"	TEXT NOT NULL,
	"steam_profile_id"	INTEGER NOT NULL,
	FOREIGN KEY("steam_profile_id") REFERENCES "steam_profile"("id") ON DELETE CASCADE,
	PRIMARY KEY("id" AUTOINCREMENT)
);
DROP TABLE IF EXISTS "steam_profile";
CREATE TABLE IF NOT EXISTS "steam_profile" (
	"id"	INTEGER NOT NULL,
	"is_public"	INTEGER,
	"name"	TEXT,
	"url"	NUMERIC,
	"avatar_url"	REAL,
	"time_created"	INTEGER,
	"last_update_time"	INTEGER,
	"last_app_update_time"	INTEGER,
	PRIMARY KEY("id")
);
COMMIT;
