
**Signup**  
**Feature Name:** User Signup  

**Kaise kaam karega:**

* Naya user website par aakar apna account bana sake.
* Form mein Username, Email, Password aur Confirm Password daalna hoga.
* Email already registered ho to error message dikhega (unique email).
* Signup complete hone par user automatically login ho jaye ya login page par redirect ho.
* Signup ke baad user ko welcome message aur dashboard par le jaya jaye.

**Extra Options:**

* Profile photo upload karne ka option signup ke time ya baad mein.
* Terms & Conditions checkbox.
* Google/Email social signup (optional future).

**Security Note:**

* Password strong hona chahiye (minimum 8 characters, letters + numbers).
* Email verification optional (link bhej kar confirm karna).

---

**Login**  
**Feature Name:** User Login  

**Kaise kaam karega:**

* Registered user Username ya Email + Password daal kar login kar sake.
* “Remember Me” checkbox se browser mein logged-in rahe.
* Galat password ya username daalne par clear error message dikhe.
* Login hone ke baad user Dashboard par redirect ho.

**Extra Options:**

* Login with Google (optional).
* “Forgot Password?” link directly.

**Security Note:**

* Brute force protection (multiple wrong attempts par captcha).
* Only logged-in users hi main features use kar sake.

---

**Logout**  
**Feature Name:** User Logout  

**Kaise kaam karega:**

* Ek click par user ko website se bahar kar de.
* Session clear ho jaye aur login page par redirect ho.

**Extra Options:**

* Confirm popup (kya aap sach mein logout karna chahte hain?).

---

**Forgot Password**  
**Feature Name:** Forgot Password  

**Kaise kaam karega:**

* User email daal kar “Reset Password” request bhej sake.
* Email mein reset link aaye.
* Link click karne par naya password set kar sake.

**Security Note:**

* Link 1 hour mein expire ho jaye.
* Sirf registered email par hi link bhejega.

---

**User Profile Page**  
**Feature Name:** User Profile  

**Kaise kaam karega:**

* User apna personal dashboard dekh sake.
* Profile photo, username, email, join date dikhe.
* Stats dikhe: Total Files, Total Groups, Storage Used.
* Recent activity log (kab kya upload kiya, kis group join kiya).

**Extra Options:**

* Profile photo edit / remove.
* Password change option.
* Account delete option.

---

**File Upload**  
**Feature Name:** File Upload  

**Kaise kaam karega:**

* User koi bhi file upload kar sake (PDF, Image, Doc, Zip etc.).
* File title daal sake.
* Option: Private (sirf khud) ya kisi Group mein upload.
* Multiple files ek saath upload kar sake.

**Extra Options:**

* File size limit (default 50MB).
* Allowed file types select.
* Drag & drop support.

**Security Note:**

* Virus scan (optional).
* Only logged-in user ya IP Group wale upload kar sake.

---

**My Files Page**  
**Feature Name:** My Files  

**Kaise kaam karega:**

* User apni saari uploaded files ek jagah dekh sake.
* List mein file name, size, date, type dikhe.
* Search aur filter (private / group / date).

**Extra Options:**

* Sort by name, size, date.
* Bulk delete.

---

**File Actions (Preview, Download, Delete)**  
**Feature Name:** File Actions  

**Kaise kaam karega:**

* Har file ke saath Preview (image/PDF), Download aur Delete button.
* Preview browser mein hi khule.

**Security Note:**

* Delete sirf owner hi kar sake.

---

**Create Group**  
**Feature Name:** Create Group  

**Kaise kaam karega:**

* User naya group bana sake.
* Group naam, description, privacy (Public/Private) set kare.
* Join type (Direct / Request based) choose kare.

---

**Group Detail Page**  
**Feature Name:** Group Detail Page  

**Kaise kaam karega:**

* Group kholne par naam, description, total members, total files dikhe.
* Members list aur Group Files section dikhe.
* Quick upload button.

---

**Group Roles & Permissions**  
**Feature Name:** Group Roles (Admin / Moderator / Member)  

**Kaise kaam karega:**

* Har group mein 3 roles honge.
* **Admin** (owner): full control.
* **Moderator**: add/remove members, delete files, invite link.
* **Normal Member**: upload + download only.

**Extra Options:**

* Admin moderator bana sake.

---

**Add / Remove / Ban Member**  
**Feature Name:** Member Management  

**Kaise kaam karega:**

* Admin/Moderator username/email se member add kar sake.
* Kisi member ko remove ya permanently ban kar sake.
* Banned user wapas nahi join kar sake.

---

**Join Request System**  
**Feature Name:** Join Request System  

**Kaise kaam karega:**

* Private group mein user “Join Request” bhej sake.
* Admin/Moderator approve ya reject kar sake.
* Pending requests ki list dikhe.

---

**Group Invite Link**  
**Feature Name:** Group Invite Link  

**Kaise kaam karega:**

* Admin/Moderator ek shareable link generate kar sake.
* Link expiry aur one-time use option.
* Link se direct join ya join request.

---

**File Permission per Member**  
**Feature Name:** File Permission per Member  

**Kaise kaam karega:**

* Har member ko alag permission (Viewer / Uploader / Editor).
* Admin member add karte time permission select kar sake.
* Baad mein bhi change kar sake.

---

**Default IP-Based Group (Anonymous Access)**  
**Feature Name:** IP Group / Auto IP Group  

**Kaise kaam karega:**

* Website mein ek Default Group already bana hoga jiska naam hoga "Local Network" ya "IP Shared Group".
* Jab koi bhi user (bina signup/login ke) website par aayega, uska IP address automatically detect hoga.
* Saare users jo same IP se aayenge, woh automatically is IP Group ke members maane jayenge.
* Unhe signup/login ki jarurat nahi hogi.
* Woh log is IP Group ke andar files upload kar sakenge aur dusre same IP wale users ki files dekh aur download kar sakenge.
* Files is group mein upload hone par sirf same IP wale users ko hi dikhegi.
* IP Group ke files ko public within same IP samjha jayega.

**Extra Options in IP Group:**

* Admin (aap) is IP Group ke settings change kar sake (jaise file size limit, allowed file types).
* IP Group ko enable/disable karne ka option.
* IP Group ke files ka expiry (jaise 7 din baad auto delete).
* Same IP wale users ko dashboard mein "Local Network Group" ka direct access mile.
* Agar user login kare to uske private files + normal groups + IP Group sab dikhe.

**Security Note:**

* Sirf same IP address wale log access kar sake (jaise ghar ke sabhi devices, office network, etc.).
* Bahar ke log (dusre IP se) is group ko nahi dekh sakenge.

---

**Dashboard / Home Page**  
**Feature Name:** Dashboard  

**Kaise kaam karega:**

* Login karte hi user ko dashboard dikhe.
* Recent files (private + group + IP Group).
* Active groups ke quick links.
* Stats cards aur quick upload button.

---

**Global Search**  
**Feature Name:** Global Search  

**Kaise kaam karega:**

* Top bar mein search box.
* Files aur Groups dono mein search kare.

---

**Notifications**  
**Feature Name:** Notifications  

**Kaise kaam karega:**

* New join request, new file in group, member added/removed ki notification.

---

**Activity Log**  
**Feature Name:** Activity Log  

**Kaise kaam karega:**

* Profile mein user ki saari activities dikhe (upload, group join etc.).

---

**Security & Privacy (Overall)**  
**Feature Name:** Overall Security  

**Kaise kaam karega:**

* Private files sirf owner ko.
* Group files sirf group members ko.
* IP Group files sirf same IP wale ko.
* Only logged-in users (except IP Group) main area access kar sake.

---
