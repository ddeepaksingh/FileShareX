**✅ Final Tightened Design — Sab Gaps Fixed**

Main ne aapke diye 6 critical gaps ko properly address kar diya hai. Har cheez ab **clear rule** ke saath define ki gayi hai.

---

### **1. IP + Login Merge Logic (Fixed)**  
**Feature Name:** IP Group + Login Integration  

**Kaise kaam karega:**

* IP Group files **kabhi bhi** normal "My Files" mein merge nahi hongi.
* Do alag sections honge:
  - **My Files** → Sirf logged-in user ki private files + normal groups ki files.
  - **Local Network (IP Group)** → Same IP par upload hui saari files (including dusre anonymous users ki).
* Login karne ke baad bhi user ko **IP Group** ka alag tab/section dikhega.
* User ki khud ki IP Group files ko "My IP Uploads" sub-section mein highlight kiya jayega.

**Clear Rule:**  
IP files = Network shared (sab dekh sakte hain)  
Private/Group files = Personal ownership (sirf owner + allowed members)

---

### **2. Duplicate Detection (Fixed)**  
**Feature Name:** Duplicate File Handling  

**Kaise kaam karega:**

* Har file ka SHA-256 hash calculate hoga.
* Agar same hash already exist karta hai:
  - **Option dikhega** user ko:
    1. **Reuse existing file** (storage save, reference add)
    2. **Upload as new copy** (allow duplicate)
    3. **Cancel**
* Silent skip nahi hoga.
* Agar reuse kiya to dono users ko ownership dikhega (multiple owners supported).

**Rule:** Duplicate detection warning + user choice.

---

### **3. Versioning Logic (Fixed)**  
**Feature Name:** File Versioning  

**Kaise kaam karega:**

**Version tab sirf tab banega jab:**
* Same user
* Same file name
* Same location (same folder ya same group/IP Group)

**Nahi to:**
* Nayi file maani jayegi (no versioning).

**Extra:**
* Version history button har file par.
* Purani versions ko list + download + restore option.
* Max 10 versions per file (configurable).

**Clear Trigger:** Same user + same name + same parent location = version.

---

### **4. Public Link vs IP Restriction (Fixed)**  
**Feature Name:** Public Sharing Links  

**Kaise kaam karega:**

* **Normal access** → IP restriction + login rules follow karega.
* **Public Share Link** banane par → **IP restriction bypass** ho jayega.
* Public link ke saath optional:
  - Password protection
  - Expiry time (1h to 30 days)
  - View only / Download allowed

**Clear Priority Rule:**
Public Link > IP/Group restrictions (link wale ko access milega)

---

### **5. Trash + Expiry Conflict (Fixed)**  
**Feature Name:** Delete & Expiry System  

**Kaise kaam karega:**

**IP Group Files:**
* Sirf **Expiry** system (no trash).
* Expiry hone par direct permanent delete (storage + DB se).

**Logged-in User Files (Private + Normal Groups):**
* Delete → Trash folder mein jaye.
* Trash se restore possible.
* Trash auto clean after 30 days.

**Rule:**
IP Group = Temporary nature → Expiry only  
User files = Permanent nature → Trash system

---

### **6. Rate Limit + Chunk Upload Clash (Fixed)**  
**Feature Name:** Upload Rate Limiting  

**Kaise kaam karega:**

* Rate limit **per upload session** hoga, na ki per chunk.
* Ek badi file upload karte time sirf 1 count hoga rate limit mein.
* Chunk requests ko rate limiter skip karega (ya bahut high limit).
* Progress bar + resume support rahega.

**Result:** Large files bhi smoothly upload ho sakegi bina rate limit block kiye.

---

### **Updated Minor Points (Ab Clear)**

7. **Anonymous ID** → Cookie based, delete hone par identity lost (accepted).
8. **File Ownership Transfer** → Group files mein Admin owner change kar sakega.
9. **Storage Structure** → Abstract layer banayenge (local disk ya S3 dono support).
10. **Search** → Upload ke turant baad metadata index hoga (background job), content search later.

---

**Final Architecture Rules (Solid)**

- IP Group = Temporary, Anonymous, Network-only
- User Account = Permanent, Private, Cross-device
- Expiry = IP Group only
- Trash = User files only
- Public Link = Full bypass
- Versioning = Strict same-user + same-name rule
- Duplicates = User choice

---
