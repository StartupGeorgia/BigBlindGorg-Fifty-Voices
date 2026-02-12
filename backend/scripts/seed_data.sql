-- Seed data for Fifty Voices VPS deployment
-- Run after migrations: cat seed_data.sql | docker exec -i voice-agent-postgres psql -U postgres -d voicenoob
--
-- IMPORTANT: Before running, replace OPENAI_API_KEY_HERE with your actual OpenAI API key.
-- You can also set it later via the Settings UI.

BEGIN;

-- Workspace "Fifty"
INSERT INTO workspaces (id, user_id, name, description, settings, is_default, created_at, updated_at)
VALUES (
  '90921169-c878-45e4-8ae8-959bf04c741d',
  1,
  'Fifty',
  '',
  '{"timezone": "Europe/Berlin", "booking_buffer_minutes": 15, "max_advance_booking_days": 30, "default_appointment_duration": 30, "allow_same_day_booking": true}',
  false,
  '2026-01-21 13:10:31.428248+00',
  '2026-01-21 13:10:31.428248+00'
) ON CONFLICT (id) DO NOTHING;

-- Agent "FIFTY Agent"
INSERT INTO agents (
  id, name, description, pricing_tier, system_prompt, language, enabled_tools,
  phone_number_id, enable_recording, enable_transcript, provider_config,
  is_active, is_published, total_calls, total_duration_seconds,
  created_at, updated_at, voice, turn_detection_mode, turn_detection_threshold,
  turn_detection_prefix_padding_ms, turn_detection_silence_duration_ms,
  enabled_tool_ids, temperature, max_tokens, public_id, embed_enabled,
  allowed_domains, embed_settings, initial_greeting, user_id
) VALUES (
  '29967819-2847-4138-87cd-6ad977b59a60',
  'FIFTY Agent',
  '',
  'premium',
  E'# Role & Identity\nYou are a helpful phone assistant. You help customers with questions, support requests, and general inquiries.\n\n# Language Rules\n- ALWAYS respond in English only\n- Never switch to any other language\n- If audio is unclear, say: "Sorry, I didn''t catch that. Could you repeat?"\n\n# Personality & Tone\n- Warm, concise, and confident\n- Keep responses to 2-3 sentences maximum\n- Speak at a steady, unhurried pace',
  'en-US',
  '["call_control", "crm", "bookings"]',
  '995322019445',
  true,
  true,
  '{"llm_provider": "openai-realtime", "llm_model": "gpt-realtime-2025-08-28", "stt_provider": "openai", "stt_model": "built-in", "tts_provider": "openai", "tts_model": "built-in"}',
  true,
  false,
  0,
  0,
  '2026-01-21 13:12:46.461293+00',
  '2026-02-10 12:55:55.781587+00',
  'marin',
  'normal',
  0.5,
  300,
  500,
  '{"call_control": ["end_call", "transfer_call", "send_dtmf"], "crm": ["search_customer", "create_contact"], "bookings": ["check_availability", "book_appointment", "list_appointments", "reschedule_appointment"]}',
  0.7,
  2000,
  'ag_j0MulTGI',
  true,
  '[]',
  '{"theme": "auto", "position": "bottom-right", "primary_color": "#6366f1", "greeting_message": "Hi! How can I help you today?", "button_text": "Talk to us"}',
  'Hello, I am alive',
  1
) ON CONFLICT (id) DO NOTHING;

-- Link agent to workspace
INSERT INTO agent_workspaces (id, agent_id, workspace_id, is_default, created_at, updated_at)
VALUES (
  '3a0e652a-ae9f-4ee8-9365-8c0e8e8849da',
  '29967819-2847-4138-87cd-6ad977b59a60',
  '90921169-c878-45e4-8ae8-959bf04c741d',
  false,
  '2026-01-21 13:12:46.484258+00',
  '2026-01-21 13:12:46.484258+00'
) ON CONFLICT (id) DO NOTHING;

-- User-level settings (OpenAI key, no workspace)
INSERT INTO user_settings (
  id, user_id, openai_api_key, workspace_id, created_at, updated_at,
  inxphone_username, inxphone_api_key, inxphone_device_id, inxphone_server_url, inxphone_ai_number
) VALUES (
  'ab7aefeb-eb5f-47eb-8849-0fa7399ec284',
  '43f2e40a-0efc-559a-8a82-981306f42751',
  'OPENAI_API_KEY_HERE',
  NULL,
  '2026-01-21 13:14:34.560623+00',
  '2026-01-21 13:14:34.560629+00',
  NULL, NULL, NULL, NULL, NULL
) ON CONFLICT (id) DO NOTHING;

-- Workspace-level settings (OpenAI + InXPhone config)
INSERT INTO user_settings (
  id, user_id, openai_api_key, workspace_id, created_at, updated_at,
  inxphone_username, inxphone_api_key, inxphone_device_id, inxphone_server_url, inxphone_ai_number
) VALUES (
  '4ac4610d-251e-4c74-9f08-126442df1cb2',
  '43f2e40a-0efc-559a-8a82-981306f42751',
  'OPENAI_API_KEY_HERE',
  '90921169-c878-45e4-8ae8-959bf04c741d',
  '2026-01-21 13:17:25.049836+00',
  '2026-02-12 11:51:06.980093+00',
  '2887777',
  'case123',
  '188444',
  'http://92.241.68.6/billing/api',
  '995322887777'
) ON CONFLICT (id) DO NOTHING;

COMMIT;
