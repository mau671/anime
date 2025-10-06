#!/usr/bin/env python3
"""Quick script to check if environment variables are being read."""

from app.core.config import get_settings

settings = get_settings()

print("=" * 80)
print("Environment Configuration Check")
print("=" * 80)
print(f"\n📝 TVDB Settings:")
print(f"   Base URL: {settings.tvdb.base_url}")
print(f"   API Key: {'✅ Set' if settings.tvdb.api_key else '❌ Not Set'}")
if settings.tvdb.api_key:
    print(f"   API Key (masked): {settings.tvdb.api_key[:8]}...")
print(f"   Language: {settings.tvdb.language}")
print(f"   Client Enabled: {bool(settings.tvdb.api_key)}")

print(f"\n📝 TMDB Settings:")
print(f"   Base URL: {settings.tmdb.base_url}")
print(f"   API Key: {'✅ Set' if settings.tmdb.api_key else '❌ Not Set'}")
if settings.tmdb.api_key:
    print(f"   API Key (masked): {settings.tmdb.api_key[:8]}...")
print(f"   Language: {settings.tmdb.language}")
print(f"   Client Enabled: {bool(settings.tmdb.api_key)}")

print(f"\n📝 MongoDB Settings:")
print(f"   URI: {settings.mongo_uri}")
print(f"   Database: {settings.mongo_db_name}")

print("\n" + "=" * 80)

if not settings.tvdb.api_key and not settings.tmdb.api_key:
    print("⚠️  No external API keys configured!")
    print("   Set TVDB_API_KEY and/or TMDB_API_KEY environment variables.")
elif not settings.tvdb.api_key:
    print("⚠️  TVDB API key not configured!")
    print("   Set TVDB_API_KEY environment variable.")
elif not settings.tmdb.api_key:
    print("⚠️  TMDB API key not configured!")
    print("   Set TMDB_API_KEY environment variable.")
else:
    print("✅ All external API keys are configured!")

print("=" * 80)

