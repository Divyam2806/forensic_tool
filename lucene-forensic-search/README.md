# Lucene Forensic Search Engine

A simple forensic keyword and metadata search engine built using Apache Lucene.

This project is part of the internship project:

**AI-Powered Digital Evidence Preservation & Cyber Forensics**

---

# Project Objective

The goal of this module is to simulate how forensic tools like FTK and Autopsy perform:

- Keyword searching
- Evidence indexing
- File metadata searching
- Evidence integrity verification using SHA256

This module allows investigators to search through evidence files quickly.

---

# Features

## 1. Content Search

Search inside file contents.

Example:

bitcoin
password
malware

2. Boolean Search

Supports:

password OR login
bitcoin AND wallet
malware NOT browser
3. Metadata Search

Supports:

extension:pdf
filename:log1.txt
sha256:abcd123...

Future support:

author:Michael
time_modified:2024-12-14
encrypted:true
4. SHA256 Hashing

Each file is hashed before indexing.

Used for:

evidence integrity
tamper detection
forensic authenticity
Project Structure
lucene-search/
│
├── evidence/                  # Raw evidence files
│   ├── log1.txt
│   ├── log2.txt
│   ├── book1.pdf
│
├── metadata/                  # Metadata JSON files (generated separately)
│   ├── log1.json
│   ├── book1.json
│
├── index/                     # Lucene generated index
│
├── src/
│   └── main/java/com/forensics/
│       ├── IndexFiles.java
│       ├── SearchFiles.java
│
├── pom.xml
└── README.md


Installation
Requirements
Java 17+
Maven

Check:

java -version
mvn -version
Setup

Clone repo:

git clone <repo-url>
cd lucene-search

Install dependencies:

mvn compile
Add Evidence Files

Put files inside:

evidence/

Example:

evidence/log1.txt
evidence/log2.txt
evidence/report.pdf
Index Files

Run:

mvn exec:java -Dexec.mainClass="com.forensics.IndexFiles"

This will:

read evidence files
generate SHA256 hashes
extract basic metadata
create Lucene index

Output:

Indexed: log1.txt
Indexed: log2.txt
Indexing complete.
Search Files

Basic keyword search:

mvn exec:java -Dexec.mainClass="com.forensics.SearchFiles" -Dexec.args="bitcoin"

Boolean search:

mvn exec:java -Dexec.mainClass="com.forensics.SearchFiles" -Dexec.args="password OR login"

Extension search:

mvn exec:java -Dexec.mainClass="com.forensics.SearchFiles" -Dexec.args="extension:pdf"

SHA256 search:

mvn exec:java -Dexec.mainClass="com.forensics.SearchFiles" -Dexec.args="sha256:<hash>"
How It Works
Evidence Files
      ↓
Lucene Indexing
      ↓
SHA256 Generation
      ↓
Metadata Storage
      ↓
Keyword Search
      ↓
Result Matching
Current Indexed Fields

Current:

content
filename
filepath
extension
filesize
lastModified
sha256
Future Metadata Integration

Metadata JSON files will be integrated.

Example fields:

author
created date
modified date
encrypted
hidden
format
page count

Example search:

author:Michael
time_modified:2024-12-14
encrypted:false
