# 📊 DATA FLOW DIAGRAMS - S3-like Object Storage System

## 🏗️ **SYSTEM ARCHITECTURE OVERVIEW**
```
┌─────────────┐    ┌─────────────────┐    ┌──────────────────────┐
│   Browser   │────│ Demo UI Server  │────│   Docker Network    │
│  (UI App)   │    │ (Port 8080)     │    │   (s3-network)      │
└─────────────┘    └─────────────────┘    └──────────────────────┘
                                                      │
        ┌─────────────────────────────────────────────┼─────────────────────────────────────────────┐
        │                                             │                                             │
        ▼                                             ▼                                             ▼
┌─────────────┐                              ┌─────────────┐                              ┌─────────────┐
│API Gateway  │                              │   Storage   │                              │   Identity  │
│Port: 7841   │                              │   Layer     │                              │Port: 7851   │
└─────────────┘                              └─────────────┘                              └─────────────┘
        │                                             │                                             │
        ├─── Rate Limiting                           ├─── PostgreSQL (Metadata)                   ├─── SQLite
        ├─── Authentication                          ├─── SQLite (Storage Index)                  ├─── User Management
        └─── Request Routing                         └─── File System (/data/storage)             └─── Auth Tokens

┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Bucket    │    │   Object    │    │   Storage   │    │  Metadata   │
│Port: 7861   │    │Port: 7871   │    │Port: 7881   │    │Port: 7891   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

---

## 1️⃣ **BUCKET OPERATIONS**

### **Create Bucket**
```
┌─────────────┐  POST   ┌─────────────┐  Auth   ┌─────────────┐  CREATE  ┌──────────────┐
│     UI      │ buckets │ API Gateway │ verify  │   Bucket    │  bucket  │ PostgreSQL   │
│             │────────▶│             │────────▶│   Service   │─────────▶│   Database   │
│ Bucket Form │         │ Rate Limit  │         │             │          │              │
└─────────────┘         │ + Routing   │         └─────────────┘          └──────────────┘
                        └─────────────┘                │                        │
                                                       │  ✅ Success            │  
                                                       ▼                        ▼  
                                              ┌─────────────┐            ┌─────────────┐
                                              │   Response  │            │   Stored:   │
                                              │   201 + ID  │            │ bucket_id,  │
                                              └─────────────┘            │ name, owner │
                                                                         └─────────────┘
```

### **List Buckets** 
```
┌─────────────┐   GET    ┌─────────────┐  Auth   ┌─────────────┐  SELECT  ┌──────────────┐
│     UI      │  buckets │ API Gateway │ verify  │   Bucket    │   WHERE  │ PostgreSQL   │
│             │◀────────│             │◀────────│   Service   │◀─────────│   Database   │
│ Bucket List │         │ Rate Limit  │         │             │ owner_id │              │
└─────────────┘         │ + Routing   │         └─────────────┘          └──────────────┘
       ▲                └─────────────┘                │                        ▲
       │                                               │                        │
       │                                               ▼                        │
       └─────────── JSON Array ◀─────────────  ┌─────────────┐                 │
         [{bucket_id, name, owner, created}]    │   Format    │─────────────────┘
                                                │   Response  │   
                                                └─────────────┘   
```

### **Delete Bucket**
```
┌─────────────┐ DELETE  ┌─────────────┐  Auth   ┌─────────────┐  DELETE  ┌──────────────┐
│     UI      │ bucket/ │ API Gateway │ verify  │   Bucket    │   WHERE  │ PostgreSQL   │
│             │ {name}  │             │────────▶│   Service   │  bucket  │   Database   │
│Delete Button│────────▶│ Rate Limit  │         │             │ = name   │              │
└─────────────┘         │ + Routing   │         └─────────────┘─────────▶└──────────────┘
                        └─────────────┘                │                        │
                                                       │  ✅ 204 Success        │
                                                       ▼                        ▼
                                              ┌─────────────┐            ┌─────────────┐
                                              │   Empty     │            │   Record    │
                                              │  Response   │            │   Removed   │
                                              └─────────────┘            └─────────────┘
```

---

## 2️⃣ **OBJECT OPERATIONS**

### **Upload Object (Most Complex - Storage First Pattern)**
```
┌─────────────┐   PUT    ┌─────────────┐  Auth   ┌─────────────┐          
│     UI      │ buckets/ │ API Gateway │ verify  │   Object    │          
│             │{bucket}/ │             │────────▶│   Service   │          
│File Upload  │objects/  │ Rate Limit  │         │             │          
│   Form      │{key}     │ + Routing   │         └─────────────┘          
└─────────────┘─────────▶└─────────────┘                │                 
                                                        │                 
        ┌───────────────────────────────────────────────┼─────────────────────────┐
        │                    STEP 1: Storage First      ▼                         │
        │         ┌─────────────┐   POST    ┌─────────────┐   File    ┌───────────┐│
        │         │   Object    │   /data   │   Storage   │  System   │   UUID    ││
        │         │   Service   │──────────▶│   Service   │──────────▶│ Partition ││
        │         │             │ + UUID    │             │  3-Copy   │  Storage  ││
        │         │             │ + MD5     │             │   Write   │           ││
        │         └─────────────┘           └─────────────┘           └───────────┘│
        │                    ▲                      │                              │
        │                    │                      ▼                              │
        │                    │                ┌───────────┐                       │
        │                    │                │  SQLite   │                       │
        │                    │                │  Storage  │                       │
        │                    │                │   Index   │                       │
        │                    │                └───────────┘                       │
        │                    │                                                    │
        │         ┌──────────┴─────────── ✅ 201 Success ◀─────────────────────────┘
        │         │                                                              
        │         ▼                    STEP 2: Metadata Second                   
        │  ┌─────────────┐   POST    ┌─────────────┐   INSERT   ┌──────────────┐ 
        │  │   Object    │metadata/  │  Metadata   │    INTO    │ PostgreSQL   │ 
        │  │   Service   │  objects  │   Service   │   object_  │   Database   │ 
        │  │             │──────────▶│             │  metadata  │              │ 
        │  │             │ + bucket  │             │──────────▶│              │ 
        │  └─────────────┘ + object  └─────────────┘           └──────────────┘ 
        │         │       + metadata                                            
        │         │                                                             
        │         ▼                                                             
        │  ┌─────────────┐           ┌─────────────┐                           
        │  │ ✅ SUCCESS  │           │❌ ROLLBACK  │ ◀── If metadata fails     
        │  │   Return    │           │   DELETE    │     delete from storage   
        │  │  Object ID  │           │   Storage   │                           
        │  └─────────────┘           └─────────────┘                           
        └─────────────────────────────────────────────────────────────────────┘
```

### **Download Object**
```
┌─────────────┐   GET    ┌─────────────┐  Auth   ┌─────────────┐                    
│     UI      │ buckets/ │ API Gateway │ verify  │   Object    │                    
│             │{bucket}/ │             │────────▶│   Service   │                    
│Download Link│objects/  │ Rate Limit  │         │             │                    
│             │{key}     │ + Routing   │         └─────────────┘                    
└─────────────┘─────────▶└─────────────┘                │                          
                                                        │                          
        ┌───────────────────────────────────────────────┼──────────────────────────┐
        │                 STEP 1: Get Object ID         ▼                          │
        │         ┌─────────────┐   GET     ┌─────────────┐   SELECT   ┌───────────┐│
        │         │   Object    │metadata/  │  Metadata   │    WHERE   │PostgreSQL ││
        │         │   Service   │buckets/   │   Service   │   bucket   │ Database  ││
        │         │             │{bucket}/  │             │   & name   │           ││
        │         │             │objects    │             │◀───────────│           ││
        │         └─────────────┘           └─────────────┘            └───────────┘│
        │                ▲                           │                              │
        │                │                           ▼                              │
        │                │                  ┌─────────────┐                        │
        │                │                  │   Object    │                        │
        │                └─────────────────│Metadata +ID │                        │
        │                                  └─────────────┘                        │
        │                                                                         │
        │                 STEP 2: Fetch File Data                                 │
        │         ┌─────────────┐   GET     ┌─────────────┐   Read    ┌───────────┐│
        │         │   Object    │   data/   │   Storage   │   File    │   UUID    ││
        │         │   Service   │  {uuid}   │   Service   │  System   │ Partition ││
        │         │             │──────────▶│             │──────────▶│  Storage  ││
        │         │             │           │             │           │           ││
        │         └─────────────┘           └─────────────┘           └───────────┘│
        │                ▲                           │                              │
        │                │                           ▼                              │
        │                │                  ┌─────────────┐                        │
        │                │                  │   Binary    │                        │
        │                └─────────────────│File Stream  │                        │
        │                                  └─────────────┘                        │
        └─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                          ┌─────────────┐
                          │ Stream to   │
                          │   Browser   │
                          │ + Headers   │
                          │(ETag, Size) │
                          └─────────────┘
```

### **Delete Object (Dual Cleanup)**
```
┌─────────────┐ DELETE  ┌─────────────┐  Auth   ┌─────────────┐                    
│     UI      │ buckets/ │ API Gateway │ verify  │   Object    │                    
│             │{bucket}/ │             │────────▶│   Service   │                    
│Delete Button│objects/  │ Rate Limit  │         │             │                    
│             │{key}     │ + Routing   │         └─────────────┘                    
└─────────────┘─────────▶└─────────────┘                │                          
                                                        │                          
        ┌───────────────────────────────────────────────┼──────────────────────────┐
        │                 STEP 1: Get Object ID         ▼                          │
        │         ┌─────────────┐   GET     ┌─────────────┐   SELECT   ┌───────────┐│
        │         │   Object    │metadata/  │  Metadata   │    WHERE   │PostgreSQL ││
        │         │   Service   │buckets/   │   Service   │   bucket   │ Database  ││
        │         │             │{bucket}/  │             │   & name   │           ││
        │         │             │objects    │             │◀───────────│           ││
        │         └─────────────┘           └─────────────┘            └───────────┘│
        │                │                           │                              │
        │                │                           ▼                              │
        │                │                  ┌─────────────┐                        │
        │                │                  │   Object    │                        │
        │                │                  │   ID Found  │                        │
        │                │                  └─────────────┘                        │
        │                │                                                         │
        │                ▼           STEP 2: Delete Metadata First                 │
        │         ┌─────────────┐  DELETE   ┌─────────────┐   DELETE   ┌───────────┐│
        │         │   Object    │metadata/  │  Metadata   │    FROM    │PostgreSQL ││
        │         │   Service   │ objects/  │   Service   │   object_  │ Database  ││
        │         │             │  {uuid}   │             │  metadata  │           ││
        │         │             │──────────▶│             │──────────▶│           ││
        │         └─────────────┘           └─────────────┘            └───────────┘│
        │                │                           │                              │
        │                │                           ▼                              │
        │                │                  ┌─────────────┐                        │
        │                │                  │ ✅ Metadata │                        │
        │                │                  │   Deleted   │                        │
        │                │                  └─────────────┘                        │
        │                │                                                         │
        │                ▼           STEP 3: Delete Storage (Cleanup)              │
        │         ┌─────────────┐  DELETE   ┌─────────────┐   Remove   ┌───────────┐│
        │         │   Object    │   data/   │   Storage   │  All 3     │   UUID    ││
        │         │   Service   │  {uuid}   │   Service   │   File     │ Partition ││
        │         │             │──────────▶│             │  Copies    │  Storage  ││
        │         │             │           │             │──────────▶│           ││
        │         └─────────────┘           └─────────────┘            └───────────┘│
        │                │                           │                              │
        │                │                           ▼                              │
        │                │                  ┌─────────────┐                        │
        │                │                  │ ✅ Storage  │                        │
        │                │                  │   Cleaned   │                        │
        │                │                  └─────────────┘                        │
        └─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                          ┌─────────────┐
                          │ Return 204  │
                          │  Success    │
                          └─────────────┘
```

### **List Objects (with Prefix Filtering)**
```
┌─────────────┐   GET    ┌─────────────┐  Auth   ┌─────────────┐                    
│     UI      │ buckets/ │ API Gateway │ verify  │   Object    │                    
│             │{bucket}/ │             │────────▶│   Service   │                    
│Object List  │objects   │ Rate Limit  │         │             │                    
│ + Prefix    │?prefix=  │ + Routing   │         └─────────────┘                    
└─────────────┘─────────▶└─────────────┘                │                          
                                                        │                          
        ┌───────────────────────────────────────────────┼──────────────────────────┐
        │                 Query with Filters            ▼                          │
        │         ┌─────────────┐   GET     ┌─────────────┐   SELECT   ┌───────────┐│
        │         │   Object    │metadata/  │  Metadata   │    WHERE   │PostgreSQL ││
        │         │   Service   │buckets/   │   Service   │   bucket   │ Database  ││
        │         │             │{bucket}/  │             │   & prefix │           ││
        │         │             │objects    │             │    LIKE    │           ││
        │         │             │?prefix    │             │  '{prefix}%'│          ││
        │         └─────────────┘           └─────────────┘◀───────────└───────────┘│
        │                ▲                           │                              │
        │                │                           ▼                              │
        │                │                  ┌─────────────┐                        │
        │                │                  │   Object    │                        │
        │                │                  │Metadata List│                        │
        │                │                  │ + Pagination│                        │
        │                └─────────────────│             │                        │
        │                                  └─────────────┘                        │
        └─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                          ┌─────────────┐
                          │ JSON Array  │
                          │[{object_id, │
                          │ name, size, │
                          │ etag, date}]│
                          └─────────────┘
```

---

## 3️⃣ **ADMINISTRATIVE OPERATIONS**

### **Health Checks**
```
┌─────────────┐   GET    ┌─────────────┐   Basic   ┌─────────────┐                    
│     UI      │  /health │ Each Service│   Status  │   Service   │                    
│             │────────▶│             │   Check   │   Health    │                    
│Health Button│         │ API Gateway │──────────▶│   Monitor   │                    
│             │         │Identity,etc.│           │             │                    
└─────────────┘         └─────────────┘           └─────────────┘                    
                               │                           │                          
        ┌──────────────────────┼───────────────────────────┼──────────────────────────┐
        │      PARALLEL HEALTH CHECKS TO ALL SERVICES      ▼                          │
        │                                                                             │
        │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
        │  │ API Gateway │  │  Identity   │  │   Bucket    │  │   Object    │       │
        │  │   :7841     │  │   :7851     │  │   :7861     │  │   :7871     │       │
        │  │             │  │             │  │             │  │             │       │
        │  │ ✅ Simple   │  │ ✅ SQLite   │  │ ✅ PostgreSQL│  │ ✅ Simple   │       │
        │  │   Status    │  │    Test     │  │    Test     │  │   Status    │       │
        │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
        │                                                                             │
        │  ┌─────────────┐  ┌─────────────┐                                         │
        │  │   Storage   │  │  Metadata   │                                         │
        │  │   :7881     │  │   :7891     │                                         │
        │  │             │  │             │                                         │
        │  │ ✅ File Sys │  │ ✅ PostgreSQL│                                        │
        │  │    Test     │  │    Test     │                                         │
        │  └─────────────┘  └─────────────┘                                         │
        └─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                          ┌─────────────┐
                          │ Aggregate   │
                          │ Status UI   │
                          │ ✅ All OK   │
                          │ ❌ Issues   │
                          └─────────────┘
```

### **Rate Limiting (API Gateway Middleware)**
```
┌─────────────┐    ANY    ┌─────────────┐ Rate Limit┌─────────────┐                   
│     UI      │  Request  │ API Gateway │ Middleware │   Memory    │                   
│             │────────▶  │             │──────────▶│ Rate Store  │                   
│ Any Action  │           │ Intercepts  │ Check IP  │             │                   
│             │           │ All Traffic │           │{IP: [times]}│                   
└─────────────┘           └─────────────┘           └─────────────┘                   
                                 │                           │                        
        ┌────────────────────────┼───────────────────────────┼────────────────────────┐
        │            RATE LIMIT LOGIC (100 req/min)         ▼                        │
        │                                                                             │
        │         ┌─────────────┐           ┌─────────────┐           ┌─────────────┐│
        │         │   Check     │           │   Clean     │           │   Count     ││
        │         │   Client    │           │   Old       │           │   Recent    ││
        │         │     IP      │──────────▶│  Requests   │──────────▶│  Requests   ││
        │         │             │           │ (>60s ago) │           │ (<60s ago)  ││
        │         └─────────────┘           └─────────────┘           └─────────────┘│
        │                                                                    │        │
        │         ┌─────────────┐           ┌─────────────┐                  │        │
        │         │❌ BLOCK     │           │✅ ALLOW     │                  │        │
        │         │Return 429   │◀─────────│Add timestamp│◀─────────────────┘        │
        │         │Rate Limited │ IF >100   │To list &    │ IF ≤100                   │
        │         │             │           │Continue     │                           │
        │         └─────────────┘           └─────────────┘                           │
        └─────────────────────────────────────────────────────────────────────────┘
```

---

## 4️⃣ **STATISTICS & DATA INTEGRITY OPERATIONS**

### **Storage Statistics**
```
┌─────────────┐   GET     ┌─────────────┐   Query   ┌─────────────┐                   
│     UI      │metadata/  │  Metadata   │Aggregate  │ PostgreSQL  │                   
│             │   stats   │   Service   │    SQL    │  Database   │                   
│Stats Button │──────────▶│             │──────────▶│             │                   
│             │           │             │           │object_meta  │                   
└─────────────┘           └─────────────┘           └─────────────┘                   
                                 │                           │                        
        ┌────────────────────────┼───────────────────────────┼────────────────────────┐
        │              AGGREGATION QUERIES                   ▼                        │
        │                                                                             │
        │         ┌─────────────┐           ┌─────────────┐           ┌─────────────┐│
        │         │   Global    │           │ Per-Bucket  │           │  Top 10     ││
        │         │    Stats    │           │   Stats     │           │  Buckets    ││
        │         │             │           │             │           │             ││
        │         │ COUNT(*)    │           │COUNT(*) BY  │           │ORDER BY     ││
        │         │SUM(size_bytes)│          │ bucket_name │           │object_count ││
        │         │COUNT(DISTINCT│           │             │           │   DESC      ││
        │         │ bucket_name)│           │             │           │ LIMIT 10    ││
        │         └─────────────┘           └─────────────┘           └─────────────┘│
        │                │                          │                          │     │
        │                └──────────────────────────┼──────────────────────────┘     │
        │                                           ▼                                │
        │                                  ┌─────────────┐                           │
        │                                  │   Format    │                           │
        │                                  │  JSON       │                           │
        │                                  │ Response    │                           │
        │                                  └─────────────┘                           │
        └─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                          ┌─────────────┐
                          │{total_objects,│
                          │total_size_bytes,│  
                          │bucket_count,   │
                          │top_buckets[]}  │
                          └─────────────┘
```

### **MD5 Checksum Validation (Data Integrity)**
```
┌─────────────┐  Upload   ┌─────────────┐           ┌─────────────┐                   
│     UI      │   File    │   Object    │   MD5     │   Storage   │                   
│             │──────────▶│   Service   │Calculate  │   Service   │                   
│Integrity    │           │             │──────────▶│             │                   
│ Test        │           │             │   Hash    │             │                   
└─────────────┘           └─────────────┘           └─────────────┘                   
                                 │                           │                        
        ┌────────────────────────┼───────────────────────────┼────────────────────────┐
        │                MD5 VALIDATION FLOW                ▼                        │
        │                                                                             │
        │         ┌─────────────┐           ┌─────────────┐           ┌─────────────┐│
        │         │   Upload    │           │   Storage   │           │   Verify    ││
        │         │   Phase     │           │   Phase     │           │  Download   ││
        │         │             │           │             │           │             ││
        │         │Calculate    │           │Store File + │           │Compare MD5  ││
        │         │MD5 Hash     │──────────▶│Store Hash  │──────────▶│on Download  ││
        │         │from Content │           │in Metadata │           │             ││
        │         └─────────────┘           └─────────────┘           └─────────────┘│
        │                                          │                          ▲     │
        │                                          ▼                          │     │
        │                                  ┌─────────────┐                    │     │
        │                                  │  Metadata   │                    │     │
        │                                  │   Service   │────────────────────┘     │
        │                                  │Store ETag   │                          │
        │                                  │= MD5 Hash   │                          │
        │                                  └─────────────┘                          │
        └─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                          ┌─────────────┐
                          │ ✅ MATCH    │
                          │Data Integrity│
                          │  Verified   │
                          │ ❌ MISMATCH │
                          │   Error     │
                          └─────────────┘
```

### **Transactional Rollback (Compensating Transactions)**
```
┌─────────────┐   Upload  ┌─────────────┐  Storage  ┌─────────────┐                   
│     UI      │  Request  │   Object    │   First   │   Storage   │                   
│             │──────────▶│   Service   │──────────▶│   Service   │                   
│ File Upload │           │             │           │             │                   
│             │           │             │           │             │                   
└─────────────┘           └─────────────┘           └─────────────┘                   
                                 │                           │                        
        ┌────────────────────────┼───────────────────────────┼────────────────────────┐
        │               SAGA PATTERN FLOW                    ▼                        │
        │                                                                             │
        │                        │                  ┌─────────────┐                  │
        │                        │                  │   ✅ File   │                  │
        │                        │                  │   Stored    │                  │
        │                        │                  │Successfully │                  │
        │                        │                  └─────────────┘                  │
        │                        │                           │                       │
        │                        ▼            Metadata      ▼                       │
        │                 ┌─────────────┐     Second   ┌─────────────┐              │
        │                 │   Object    │──────────────▶│  Metadata   │              │
        │                 │   Service   │               │   Service   │              │
        │                 │             │               │             │              │
        │                 └─────────────┘               └─────────────┘              │
        │                        │                           │                       │
        │                        │                           ▼                       │
        │                        │                  ┌─────────────┐                  │
        │    ┌─────────────┐     │                  │❌ FAILURE   │                  │
        │    │   SUCCESS   │     │                  │Service Down │                  │
        │    │   Return    │◀────┴─── ✅ Success    │Connection   │                  │
        │    │  Object ID  │                        │   Error     │                  │
        │    └─────────────┘                        └─────────────┘                  │
        │                                                  │                         │
        │                                                  ▼                         │
        │                                          ┌─────────────┐                   │
        │                                          │🔄 ROLLBACK  │                   │
        │                                          │ Compensate  │                   │
        │                                          │DELETE from  │                   │
        │                                          │ Storage     │                   │
        │                                          └─────────────┘                   │
        │                                                  │                         │
        │                                                  ▼                         │
        │                                          ┌─────────────┐                   │
        │                                          │❌ Return    │                   │
        │                                          │503 Service  │                   │
        │                                          │Unavailable  │                   │
        │                                          └─────────────┘                   │
        └─────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 **KEY DATA FLOW PATTERNS**

### **1. Storage-First Pattern (Upload Operations)**
- **Rationale**: Easier to clean up orphaned files than missing files
- **Flow**: Storage → Metadata → Success OR Rollback Storage
- **Benefit**: Prevents data loss scenarios

### **2. Microservice Communication Patterns**
```
Browser ──CORS──▶ UI Server ──HTTP──▶ Docker Network ──Internal──▶ Services
   ▲                                                                    │
   │                                                                    ▼
   └─────────────── JSON/Streaming Response ◀──────────── Service Responses
```

### **3. Authentication Flow (API Gateway)**
```
Request ──▶ Rate Limit Check ──▶ Auth Validation ──▶ Service Route ──▶ Response
           (429 if exceeded)      (401 if invalid)     (503 if down)     (200/etc)
```

### **4. Data Persistence Strategy**
- **PostgreSQL**: Searchable metadata (buckets + objects)
- **SQLite**: Service-specific indexes (storage + identity)  
- **File System**: Raw object data with UUID partitioning
- **In-Memory**: Rate limiting and temporary state

### **5. Error Handling & Rollback**
- **Compensating Transactions**: Saga pattern for distributed consistency
- **Graceful Degradation**: Services continue operating despite partial failures
- **Cleanup Guarantees**: No orphaned data even with service outages

---

## 📊 **SUPPORTED UI OPERATIONS SUMMARY**

| Operation | HTTP Method | Primary Service | Secondary Services | Data Flow Complexity |
|-----------|-------------|-----------------|-------------------|---------------------|
| **Create Bucket** | POST | Bucket | API Gateway | Simple |
| **List Buckets** | GET | Bucket | API Gateway | Simple |  
| **Delete Bucket** | DELETE | Bucket | API Gateway | Simple |
| **Upload Object** | PUT | Object | Storage + Metadata | Complex (2-phase) |
| **Download Object** | GET | Object | Storage + Metadata | Medium (2-step) |
| **Delete Object** | DELETE | Object | Storage + Metadata | Medium (dual cleanup) |
| **List Objects** | GET | Object | Metadata | Medium (filtered query) |
| **Health Checks** | GET | All Services | None | Simple (parallel) |
| **Statistics** | GET | Metadata | None | Medium (aggregation) |
| **Rate Limiting** | Middleware | API Gateway | None | Simple (in-memory) |
| **Data Integrity** | Built-in | All Operations | None | Complex (checksums) |
| **Rollback Demo** | Simulation | Object + Storage | Metadata (down) | Complex (saga pattern) |

This comprehensive data flow documentation shows how each UI operation flows through the microservices architecture, demonstrating the sophisticated distributed system design behind your S3-like object storage implementation! 🚀

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Create data flow diagrams for bucket operations", "status": "completed", "activeForm": "Creating data flow diagrams for bucket operations"}, {"content": "Create data flow diagrams for object operations", "status": "in_progress", "activeForm": "Creating data flow diagrams for object operations"}, {"content": "Create data flow diagrams for administrative operations", "status": "pending", "activeForm": "Creating data flow diagrams for administrative operations"}, {"content": "Create data flow diagrams for health and statistics", "status": "pending", "activeForm": "Creating data flow diagrams for health and statistics"}]