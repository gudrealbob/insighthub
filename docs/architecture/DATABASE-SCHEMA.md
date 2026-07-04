## **🧱 Objective: Design PostgreSQL Schema (MVP-ready)**

We are NOT writing SQL yet.

We are designing a structure that:

- survives 6 months of evolution
- supports multiple channels later
- supports AI later
- supports analytics later
- does NOT require redesign every sprint

---

# **🧠 Core Design Decision (very important)**

We will store data in **3 layers**:

## **1. Raw Layer (immutable truth)**

Store exactly what Telegram sends.

## **2. Processed Layer (structured signals)**

Extracted trading signals.

## **3. Analytics Layer (computed results)**

Performance, win/loss, returns.

# **🧱 Final MVP Schema Design**

## **1.**

`messages` **(RAW layer)**

This is EVERYTHING from Telegram.



messages

--------

id (PK)

channel_name

message_id (telegram id)

message_text

message_date

tags (jsonb)

raw_json (jsonb)

is_processed

created_at

### **Why this exists**

- We NEVER lose original data
- We can reprocess later with better AI
- Debugging becomes easy
- Future models depend on this

---





## **2.**

`recommendations` **(STRUCTURED layer)**

This is the CORE of InsightHub.

recommendations

---------------

id (PK)

message_id (FK -> messages)

ticker

asset_class (stock/crypto/etc)

entry_price

buy_zone_low

buy_zone_high

stop_loss

target_price

pattern (cup_handle, breakout, flag, etc)

signal_type (freshview/update/partial_exit)

confidence_score

status (active/closed/invalid)

created_at

updated_at





## **3.**

`recommendation_events` **(history tracking)**

Because updates matter in your data:



recommendation_events

---------------------

id (PK)

recommendation_id (FK)

event_type (update, partial_booking, target_hit, sl_hit)

event_text

event_date

created_at

recommendation_events

---------------------

id (PK)

recommendation_id (FK)

event_type (update, partial_booking, target_hit, sl_hit)

event_text

event_date

created_at





## **4.**

`price_history` **(for analytics)**

We need this for performance calculation.

price_history

-------------

id

ticker

price

timestamp

source

(We’ll populate this later using Yahoo Finance or similar)

---





## **5.**

`recommendation_metrics` **(computed layer)**

This is what you will query for analytics.



recommendation_metrics

----------------------

id

recommendation_id

max_profit_pct

current_return_pct

hit_target (bool)

hit_sl (bool)

duration_days

calculated_at

# **🔥 Key Design Principles (IMPORTANT)**

## **1. Always store raw first**

Never trust parsing 100%.

## **2. Structured data is derived, not original**

We can always rebuild it.

## **3. Events matter more than final state**

Because analysts update calls.

## **4. Metrics are disposable**

We can recompute anytime.

---

# **🧩 Why this design is strong**

This gives you:

### **✔ Analytics**

- win rate
- avg return
- best channel
- best pattern

### **✔ AI capability later**

- “why did this trade work?”

### **✔ Debugging**

- replay everything from raw messages

### **✔ Flexibility**

- new channels = no schema change

---

# **⚠️ What we are NOT doing yet**

To keep MVP tight:

❌ No indexes optimization  
❌ No partitions  
❌ No data warehouse  
❌ No BI tools  
❌ No AI embeddings  
❌ No streaming pipeline

We add those later ONLY if needed.