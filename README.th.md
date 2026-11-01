# promo-packet

[English](README.md) · จากคนทำ [staff-katas](https://github.com/nuttakulsv/staff-katas) และ [engineering-ladder-th](https://github.com/nuttakulsv/engineering-ladder-th)

ถึงช่วงขอเลื่อนตำแหน่ง เปิดเอกสารเปล่าชื่อ "Staff promotion case" ขึ้นมา รู้สึกลางๆ ว่าปีนี้ทำอะไรไปเยอะ แต่พอไล่ดู GitHub ก็นึกไม่ออกว่า PR เดือนมีนาคมนั้นทำไปเพื่ออะไร พิมพ์ว่า "ปรับปรุง CI" แล้วก็ลบทิ้ง

promo-packet เป็น skill สำหรับ coding agent พร้อมสคริปต์ ที่ช่วยเปลี่ยนงานทั้งปีให้เป็นเอกสารขอเลื่อนตำแหน่ง (promotion packet) ที่ซื่อตรงและมีหลักฐานทุกข้อ

1. **รวบรวมหลักฐาน** `evidence.py` ดึงงานทั้งปีของเราจาก GitHub ได้แก่ PR ที่ merge แล้ว แยกตาม repo และหมวดงาน, PR ที่ใหญ่ที่สุดและที่มีคนคุยกันเยอะที่สุด, design doc, งาน CI และ infrastructure, ทุกรีวิวที่เราให้คนอื่นและเรารีวิวงานใครบ้าง, และ issue ที่เราเปิด ทุกบรรทัดมีลิงก์กลับไปหาของจริง
2. **สัมภาษณ์เรา** เรื่องที่ GitHub มองไม่เห็น เช่น ปัญหาเบื้องหลังแต่ละโปรเจกต์ เราตัดสินใจอะไร ใครทำอะไรบ้าง ตัวเลขผลลัพธ์ incident ที่เรานำแก้ คนที่เราช่วยสอน
3. **ร่างเอกสาร** เริ่มจากผลลัพธ์ก่อน ทุกข้ออ้างมีลิงก์หลักฐาน หรือมีช่องว่างให้เติมว่า `[number needed]` ไม่มีการแต่งตัวเลขเอง
4. **ทำตัวเป็นกรรมการที่ช่างสงสัย** ให้คะแนนแต่ละด้านของ rubric ว่าแข็ง พอมี หรือบาง บอกตรงๆ ว่าเรื่องไหนยังเป็นงานระดับปัจจุบัน ไม่ใช่ระดับที่ขอ และเสนอแผนปิดช่องว่าง

## หน้าตาของหลักฐาน

```
$ python3 evidence.py --since 2025-11-01 --org acme

# Evidence: @you, 2025-11-01 to 2026-11-01 (org: acme)

## At a glance
- 143 PRs merged across 9 repositories in 1 organisation(s)
- 211 reviews on 167 other people's PRs, by 23 different authors
...
Repositories where you reviewed but didn't merge anything (influence outside your own code):
acme/mobile (31), acme/search (12)
...
## Not in here
Fill these in yourself. They're often what decides a staff promotion: ...
```

ชื่อ PR ภาษาไทยก็จัดหมวดได้ เช่น "แก้ยอดรวมตะกร้าไม่ตรง" จะเข้าหมวด Fixes

## ติดตั้ง

Claude Code

```
/plugin marketplace add nuttakulsv/promo-packet
/plugin install promo-packet@promo-packet
```

Codex, Cursor หรือ agent อื่นที่อ่าน SKILL.md ได้

```
npx skills add nuttakulsv/promo-packet
```

จากนั้นพิมพ์ว่า "ช่วยเขียน promotion packet ขึ้น staff ให้หน่อย" มันจะถามระดับที่ต้องการ ladder ของบริษัท (ถ้าไม่มีจะใช้ [rubric ที่แถมไว้](skills/promo-packet/rubric.md) หรือดู ladder ภาษาไทยที่ [engineering-ladder-th](https://github.com/nuttakulsv/engineering-ladder-th)) และช่วงเวลาที่จะสรุป

สคริปต์เก็บหลักฐานใช้แยกเดี่ยวๆ ได้ ต้องมี `python3` และ [GitHub CLI](https://cli.github.com/) ที่ล็อกอินแล้ว

```
curl -O https://raw.githubusercontent.com/nuttakulsv/promo-packet/main/skills/promo-packet/evidence.py
python3 evidence.py                               # 12 เดือนล่าสุด
python3 evidence.py --since 2026-01-01 --org acme --json evidence.json
```

## ข้างในมีอะไร

- [`SKILL.md`](skills/promo-packet/SKILL.md) ขั้นตอนทั้งหมด: เก็บหลักฐาน สัมภาษณ์ ร่าง และวิจารณ์
- [`evidence.py`](skills/promo-packet/evidence.py) ค้นข้อมูลบน GitHub ผ่าน `gh` อ่านอย่างเดียว ไม่มีอะไรออกจากเครื่องนอกจากคำค้นเอง
- [`rubric.md`](skills/promo-packet/rubric.md) rubric กลางๆ ของระดับ senior / staff / principal บอกว่าหลักฐานแบบไหนน่าเชื่อในแต่ละด้าน และแบบไหนไม่ช่วย
- [`packet-template.md`](skills/promo-packet/packet-template.md) โครงเอกสารแบบที่กรรมการมักชอบ

## ใช้กับเรื่องอื่นได้ด้วย

- **self-review และการประเมินผลงาน** ขั้นตอนเดียวกันแต่สั้นกว่า
- **brag document** รันทุกเดือน แล้วจดเรื่องราวไว้ตอนที่ยังจำได้
- **หัวหน้าที่เขียนให้ลูกทีม** รันด้วย `--user` ของลูกทีม แล้วให้ agent สัมภาษณ์เราว่าเห็นอะไรบ้าง

## ควรรู้

- GitHub บอกได้ว่าทำอะไร แต่ไม่ได้บอกว่าเกิดผลอะไร เนื้อหาจริงของเอกสารมาจากช่วงสัมภาษณ์
- หมวดงานเดาจากชื่อ PR, label และ path ของไฟล์ (มีคำภาษาอังกฤษและไทย) ควรตรวจอีกรอบ
- จำนวนบรรทัดรวมไฟล์ที่ generate และ lockfile ด้วย ใช้เป็นบริบทได้ แต่ไม่ใช่ผลงาน
- ถ้างานอยู่ใน repo private บัญชี `gh` ต้องเข้าถึง repo นั้นได้ และผลจะออกมาที่ terminal ระวังเวลาเอาไปแปะที่อื่น

## อ่านต่อ

- Will Larson, [Staff archetypes](https://staffeng.com/guides/staff-archetypes/)
- [Dropbox engineering career framework](https://dropbox.github.io/dbx-career-framework/)
- Julia Evans, [Get your work recognized: write a brag document](https://jvns.ca/blog/brag-documents/)

## รันเทสต์

```
python3 skills/promo-packet/evidence.py --test
```

## License

MIT
