# Daechung Demo20 distribution release audit

dataset_role = Human-reviewed Daechung Demo20 3-class GT distribution copy

Build start: 2026-09-09T10:51:49.280907+00:00
Audit time: 2026-09-09T10:56:44.844323+00:00

Authoritative source: `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1`
Original freeze documents: `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/freeze_audit_v1`

Source audit passed before this new release root was created. Existing paths were not overwritten. All 40 dataset files and all three freeze documents were copied byte-for-byte; JSON was parsed only for validation and preview rendering, never serialized back to any dataset file.

## Results

```text
DAECHUNG_DEMO20_GITHUB_DISTRIBUTION_BUILD = PASS
release_root = /data/disks/hdd03/gookhyun/Daechung_SAM3/Daechung_Demo20_GT_release_v1
source_jpg = 20
source_json = 20
release_jpg = 20
release_json = 20
pairing = 20/20
imagePath_pairing = 20/20
json_parse = 20/20
decode = 20/20
resolution_5280x3956 = 20/20
RGB = 20/20
preview_count = 20
total_crc = 312
total_dlm = 86
total_spl = 231
total_shapes = 629
crc_linestrip_valid = 312/312
dlm_polygon_valid = 86/86
spl_polygon_valid = 231/231
total_delete_roi = 0
total_other_labels = 0
invalid_coordinate = 0
NaN_inf = 0
degenerate_geometry = 0
release_images_identical_to_source = PASS
release_json_identical_to_source = PASS
release_docs_identical_to_source = PASS
source_files_unchanged = PASS
freeze_audit_files_unchanged = PASS
README = PASS
SHA256SUMS = PASS
RELEASE_AUDIT = PASS
READY_FOR_GITHUB_UPLOAD = YES
inference_run = NO
annotation_modified = NO
source_json_rewritten = NO
existing_files_modified = 0
created_files = 66
sha256_manifest_entries = 65
```

## Validation details

- Source hashes matched the existing freeze manifest: 40/40. The original freeze CSV reported CRC hash PASS for all 20 JSON files. Entire JSON byte identity preserves that CRC baseline as well as the final DLM/SPL annotation values.
- Basename pairing is unique. imagePath pairing uses 01_Dataset/images as the lookup root: each unchanged imagePath equals its paired JPG basename. Because labels and images are split, imagePath alone is not a relative filesystem path from labels/ to images/. README explains the required lookup root and a separate co-located working-copy option.
- Full JPEG main-image decode, RGB channels, and JSON image dimensions passed for 20/20. No dataset image was resized or re-encoded.
- CRC points have at least two finite xy coordinates and positive linestrip length. DLM/SPL polygons have at least three distinct finite vertices, positive area, and valid GEOS topology. Coordinates fall within [0, 5279] × [0, 3955], tolerance 1e-6 pixels. JSON metadata and label/shape_type combinations passed. No annotation repair was performed.
- Previews were generated only from the copied final reviewed JSON files: green CRC, blue DLM, yellow SPL; translucent polygon fills. Each of the 20 preview JPG files decoded successfully at 2200 × 1802, including the header/footer. Previews are visualizations, not GT.
- Authoritative source 40 files and freeze audit 3 files: SHA256, size, mtime_ns, ctime_ns, atime_ns, inode, device, mode, uid, gid and nlink were compared before/after. O_NOATIME was used when reading protected files. File inventories remained unchanged.
- No inference, annotation changes, source JSON rewrite, min100 filtering, RDP simplification, training or upload was performed.

## Per-image final annotations

| JSON | Year | CRC | DLM | SPL | Pairing / decode / identity / geometry |
|---|---:|---:|---:|---:|---|
| DJI_20250702150745_0300_V.json | 2025 | 56 | 9 | 22 | PASS |
| DJI_20250702151015_0500_V.json | 2025 | 29 | 7 | 40 | PASS |
| DJI_20250702160538_0800_V.json | 2025 | 31 | 7 | 13 | PASS |
| DJI_20250702160658_0900_V.json | 2025 | 13 | 7 | 7 | PASS |
| DJI_20250702162237_0020_V.json | 2025 | 0 | 0 | 2 | PASS |
| DJI_20250702162257_0040_V.json | 2025 | 5 | 0 | 4 | PASS |
| DJI_20250702164518_0050_V.json | 2025 | 13 | 1 | 1 | PASS |
| DJI_20250702165251_0480_V.json | 2025 | 16 | 1 | 0 | PASS |
| DJI_20260826093331_0020_V.json | 2026 | 16 | 3 | 7 | PASS |
| DJI_20260826094118_0100_V.json | 2026 | 6 | 7 | 26 | PASS |
| DJI_20260826094549_0300_V.json | 2026 | 21 | 5 | 19 | PASS |
| DJI_20260826094700_0360_V.json | 2026 | 22 | 15 | 22 | PASS |
| DJI_20260826102236_0200_V.json | 2026 | 4 | 10 | 22 | PASS |
| DJI_20260826102412_0300_V.json | 2026 | 3 | 1 | 1 | PASS |
| DJI_20260826112900_0100_V.json | 2026 | 13 | 0 | 2 | PASS |
| DJI_20260826114456_1000_V.json | 2026 | 7 | 0 | 4 | PASS |
| DJI_20260826120100_0500_V.json | 2026 | 10 | 2 | 7 | PASS |
| DJI_20260826120256_0600_V.json | 2026 | 35 | 0 | 8 | PASS |
| DJI_20260826124557_0200_V.json | 2026 | 8 | 3 | 7 | PASS |
| DJI_20260826125854_0900_V.json | 2026 | 4 | 8 | 17 | PASS |

## Protected source before/after evidence

The SHA256 shown is the before value and equals the after value for every PASS row. Size/mtime are recorded explicitly; every additional metadata field listed above also matched.

| File | SHA256 before = after | Size before / after | mtime_ns before / after | Status |
|---|---|---:|---|---|
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702150745_0300_V.JPG` | `c9cd0503b3b30798310482cdfac208e13640189d9c34922d238db3121872c928` | 12038144 / 12038144 | 1788949929700041852 / 1788949929700041852 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702150745_0300_V.json` | `1d9952cc4b7b9253bd08cfac51f6ef6589ecbae820f82b44b051c4576c1e3cc8` | 1220459 / 1220459 | 1788950023944099034 / 1788950023944099034 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702151015_0500_V.JPG` | `90040342718953483bb4f17c87103acab594f2bcc14cc9da3f55d4cfd696cff1` | 12410880 / 12410880 | 1788949929707041931 / 1788949929707041931 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702151015_0500_V.json` | `e762cebeb3239765a0bcb197ad5ffb07cf29390e94d39d18552f36e88730151d` | 1680533 / 1680533 | 1788950023992099567 / 1788950023992099567 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702160538_0800_V.JPG` | `d830810878048c7edf4cd6d51aa3d80eaf62dc3a908e7fdaa48c7914c0530a72` | 10870784 / 10870784 | 1788949929713041999 / 1788949929713041999 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702160538_0800_V.json` | `f5664eba851dca51a01ceef86c8cfc6430f0c6bd1bb7a5cca6b31dd99eb7d89c` | 721087 / 721087 | 1788950024014099812 / 1788950024014099812 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702160658_0900_V.JPG` | `0929ecee61ac6d89992864411f05da04ac7f9d6cb05925453a1972778a464655` | 12615680 / 12615680 | 1788949929720042079 / 1788949929720042079 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702160658_0900_V.json` | `9995a2fddde4c2e79069b1fd697f78d331d6f9842c532d306d80195db02830ff` | 551039 / 551039 | 1788950024033695900 / 1788950024033695900 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702162237_0020_V.JPG` | `f433b06f92ee6eab3f5dfcf0fbef0e2561eaa3f4373090571a9b57f2669dda41` | 10747904 / 10747904 | 1788949929726042147 / 1788949929726042147 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702162237_0020_V.json` | `41ab3c8003d82824f3eb399e03a182f7b17edb02855870e5fe6b0516a3c4305f` | 99540 / 99540 | 1788950024039100090 / 1788950024039100090 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702162257_0040_V.JPG` | `306109579205e79e01ce3e13e3fb60007f5090607a39b477d01fc08c8dc563ff` | 11653120 / 11653120 | 1788949929732042214 / 1788949929732042214 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702162257_0040_V.json` | `3840354dadaa2f9f48a831f63dde86bd0ac9485b55e4350912c08ba8d5188ed0` | 1672007 / 1672007 | 1788950024097214910 / 1788950024097214910 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702164518_0050_V.JPG` | `c0d2fb8d4256e76988183542c4cdeb44dc3d583136f14107a42faa1cd7753071` | 11358208 / 11358208 | 1788949929739042294 / 1788949929739042294 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702164518_0050_V.json` | `b3c7c4e6312853ffc8be033391127aed9e35fb52f85b91a36476f073559d6b89` | 415601 / 415601 | 1788950024110100878 / 1788950024110100878 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702165251_0480_V.JPG` | `72994c4abcfcfdedfb57cca1c285867119746e027644dfe637d0776c94db12d3` | 12288000 / 12288000 | 1788949929746042373 / 1788949929746042373 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20250702165251_0480_V.json` | `70fa04acce6980905b6312298e143545e08a9f8af4e03bc0f5892afb689cd195` | 44361 / 44361 | 1788950024114100923 / 1788950024114100923 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826093331_0020_V.JPG` | `260b289bae7f3c038bda4d4d321a93750ebeb0e15354199245b8bb5fd71cb1d8` | 8687616 / 8687616 | 1788949929751042430 / 1788949929751042430 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826093331_0020_V.json` | `64156f8e84f326956c71737cf0217c042deed7ac086ec960037716e7bfb87ff4` | 189268 / 189268 | 1788950024121101001 / 1788950024121101001 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826094118_0100_V.JPG` | `3be9f9f124c6165c36489c5a966a6e90007eab404cb584b12d000a91268cadba` | 8122368 / 8122368 | 1788949929755042475 / 1788949929755042475 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826094118_0100_V.json` | `0603e00643b371e6527f8a4c2e7c8ec81f205a98943bb4fd31b310b46a9af2d2` | 1284912 / 1284912 | 1788950024157101401 / 1788950024157101401 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826094549_0300_V.JPG` | `8d3f5b49c128115090226eda09caecdbe39f241ac1eee45703184997d6fa8bee` | 8171520 / 8171520 | 1788949929760042532 / 1788949929760042532 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826094549_0300_V.json` | `3214c30dc493aba1afc6fbdc393c084ddabefdd32e454c427ea21c0f90ea2536` | 1303574 / 1303574 | 1788950024193101801 / 1788950024193101801 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826094700_0360_V.JPG` | `ebdab8a0a333c17fb523ef061dafcbe3748a4317a347f0b8167623ab300c44f3` | 9125888 / 9125888 | 1788949929765042589 / 1788949929765042589 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826094700_0360_V.json` | `c8e548ef8d19e0d6f05accd14fcb682689e2ee742b29d106af7d8a1e89c85711` | 2339022 / 2339022 | 1788950024252102457 / 1788950024252102457 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826102236_0200_V.JPG` | `7754855c9e263b6ce274b8c14684ed696920309468baf92fbe19726af41047b3` | 9183232 / 9183232 | 1788949929770042645 / 1788949929770042645 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826102236_0200_V.json` | `788cefe6db7fd928e4c6f0a096eae05fc33626e4ac890ebd0bd0b7a67cc4e4f0` | 1577465 / 1577465 | 1788950024294102924 / 1788950024294102924 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826102412_0300_V.JPG` | `76863416905832509b7900ae9201eb9a74c6d3bcece3711c227c68cad6516e88` | 9809920 / 9809920 | 1788949929776042713 / 1788949929776042713 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826102412_0300_V.json` | `f660348b0082a5f8544373d939b0c1dc7ca2a902683b3e515b013baf30b9de0a` | 13748 / 13748 | 1788950024298102969 / 1788950024298102969 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826112900_0100_V.JPG` | `9e088cb8e367f2863cb02e395556b5a90638380a8180c4b9f127e777dddafd9f` | 9469952 / 9469952 | 1788949929781042769 / 1788949929781042769 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826112900_0100_V.json` | `61d4794eaea7c71cd4ea309f1e830c4a4b7eaf776399ee12c0f8bc03743e7ae8` | 100361 / 100361 | 1788950024303391364 / 1788950024303391364 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826114456_1000_V.JPG` | `a8866567ac14061314e2372a223245a19f90b525620a4a9cb194f9a2f3c3d2a1` | 10543104 / 10543104 | 1788949929787159870 / 1788949929787159870 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826114456_1000_V.json` | `70f3fdb63cb7b2078dec1ab64cc2f02d74885be5c69e9301747bf07d282e4e4c` | 163716 / 163716 | 1788950024309103091 / 1788950024309103091 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826120100_0500_V.JPG` | `0bcbe7a31ac0d65709d839d73889b863588fbaa586071b02ed6f5b04e9647f63` | 11513856 / 11513856 | 1788949929794042917 / 1788949929794042917 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826120100_0500_V.json` | `ff5f023e6d2f2c998006b3798fcf6e3a1d88afef99d138ac85d7041d23c3157f` | 465130 / 465130 | 1788950024325103268 / 1788950024325103268 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826120256_0600_V.JPG` | `15c6691a02c681bec916630b0d8ee32f7bb718b88fadcc7418e026dbd7782b25` | 10506240 / 10506240 | 1788949929799042974 / 1788949929799042974 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826120256_0600_V.json` | `9cf2ffb3ce85eb72d58148d04cf25e69e28a06b3d37ca7f5b8e3089315d5b127` | 1035077 / 1035077 | 1788950024352103569 / 1788950024352103569 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826124557_0200_V.JPG` | `9ce15e0e4b3600ef34e646354c48bccb97df33a25d536e81292a7e3a9f373b45` | 14032896 / 14032896 | 1788949929807043064 / 1788949929807043064 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826124557_0200_V.json` | `9d64bfb7104858660808970498578867df086990828aaeb7c161137489910af2` | 1499101 / 1499101 | 1788950023863591673 / 1788950023863591673 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826125854_0900_V.JPG` | `d8e87f7dfbbd773202c0a5a950d73a6bfc4ed961604bf34345a3392ed60bfcd9` | 12300288 / 12300288 | 1788949929814043143 / 1788949929814043143 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/final_v1/DJI_20260826125854_0900_V.json` | `5d98a0a97035bb1c91e6d46c17c96b8cbda304acae4fe664d8d174ab31f6fdad` | 1884679 / 1884679 | 1788950023911098667 / 1788950023911098667 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/freeze_audit_v1/final_3class_freeze_report.md` | `028006b2293da282e2cb8c69780293dc2b68269672ebcb1564d381843cd8635e` | 64321 / 64321 | 1788950731348386050 / 1788950731348386050 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/freeze_audit_v1/final_3class_manifest.csv` | `b3bf322e58a16641d41fcec2a4cc7593cd6b21318b1f7f7c52b10bef7b20e875` | 18400 / 18400 | 1788950731293125534 / 1788950731293125534 | PASS |
| `/data/disks/hdd03/gookhyun/Daechung_SAM3/demo20_stagec_dlm_spl_v1/06_reviewed_dlm_spl/freeze_audit_v1/final_3class_sha256.txt` | `e678a0c43dc3c7c641db416c3c35e4778951fb56fb22158a16a78ac34d06d3c6` | 3860 / 3860 | 1788950731323364232 / 1788950731323364232 | PASS |

## Generated and modified files

Created: 66 files under the new release root. Modified pre-existing files: 0. No source files were moved. SHA256SUMS.txt lists 65 release-relative files and excludes itself.

```text
01_Dataset/images/DJI_20250702150745_0300_V.JPG
01_Dataset/images/DJI_20250702151015_0500_V.JPG
01_Dataset/images/DJI_20250702160538_0800_V.JPG
01_Dataset/images/DJI_20250702160658_0900_V.JPG
01_Dataset/images/DJI_20250702162237_0020_V.JPG
01_Dataset/images/DJI_20250702162257_0040_V.JPG
01_Dataset/images/DJI_20250702164518_0050_V.JPG
01_Dataset/images/DJI_20250702165251_0480_V.JPG
01_Dataset/images/DJI_20260826093331_0020_V.JPG
01_Dataset/images/DJI_20260826094118_0100_V.JPG
01_Dataset/images/DJI_20260826094549_0300_V.JPG
01_Dataset/images/DJI_20260826094700_0360_V.JPG
01_Dataset/images/DJI_20260826102236_0200_V.JPG
01_Dataset/images/DJI_20260826102412_0300_V.JPG
01_Dataset/images/DJI_20260826112900_0100_V.JPG
01_Dataset/images/DJI_20260826114456_1000_V.JPG
01_Dataset/images/DJI_20260826120100_0500_V.JPG
01_Dataset/images/DJI_20260826120256_0600_V.JPG
01_Dataset/images/DJI_20260826124557_0200_V.JPG
01_Dataset/images/DJI_20260826125854_0900_V.JPG
01_Dataset/labels/DJI_20250702150745_0300_V.json
01_Dataset/labels/DJI_20250702151015_0500_V.json
01_Dataset/labels/DJI_20250702160538_0800_V.json
01_Dataset/labels/DJI_20250702160658_0900_V.json
01_Dataset/labels/DJI_20250702162237_0020_V.json
01_Dataset/labels/DJI_20250702162257_0040_V.json
01_Dataset/labels/DJI_20250702164518_0050_V.json
01_Dataset/labels/DJI_20250702165251_0480_V.json
01_Dataset/labels/DJI_20260826093331_0020_V.json
01_Dataset/labels/DJI_20260826094118_0100_V.json
01_Dataset/labels/DJI_20260826094549_0300_V.json
01_Dataset/labels/DJI_20260826094700_0360_V.json
01_Dataset/labels/DJI_20260826102236_0200_V.json
01_Dataset/labels/DJI_20260826102412_0300_V.json
01_Dataset/labels/DJI_20260826112900_0100_V.json
01_Dataset/labels/DJI_20260826114456_1000_V.json
01_Dataset/labels/DJI_20260826120100_0500_V.json
01_Dataset/labels/DJI_20260826120256_0600_V.json
01_Dataset/labels/DJI_20260826124557_0200_V.json
01_Dataset/labels/DJI_20260826125854_0900_V.json
02_Previews/DJI_20250702150745_0300_V_final_overlay.jpg
02_Previews/DJI_20250702151015_0500_V_final_overlay.jpg
02_Previews/DJI_20250702160538_0800_V_final_overlay.jpg
02_Previews/DJI_20250702160658_0900_V_final_overlay.jpg
02_Previews/DJI_20250702162237_0020_V_final_overlay.jpg
02_Previews/DJI_20250702162257_0040_V_final_overlay.jpg
02_Previews/DJI_20250702164518_0050_V_final_overlay.jpg
02_Previews/DJI_20250702165251_0480_V_final_overlay.jpg
02_Previews/DJI_20260826093331_0020_V_final_overlay.jpg
02_Previews/DJI_20260826094118_0100_V_final_overlay.jpg
02_Previews/DJI_20260826094549_0300_V_final_overlay.jpg
02_Previews/DJI_20260826094700_0360_V_final_overlay.jpg
02_Previews/DJI_20260826102236_0200_V_final_overlay.jpg
02_Previews/DJI_20260826102412_0300_V_final_overlay.jpg
02_Previews/DJI_20260826112900_0100_V_final_overlay.jpg
02_Previews/DJI_20260826114456_1000_V_final_overlay.jpg
02_Previews/DJI_20260826120100_0500_V_final_overlay.jpg
02_Previews/DJI_20260826120256_0600_V_final_overlay.jpg
02_Previews/DJI_20260826124557_0200_V_final_overlay.jpg
02_Previews/DJI_20260826125854_0900_V_final_overlay.jpg
03_Docs/final_3class_freeze_report.md
03_Docs/final_3class_manifest.csv
03_Docs/final_3class_sha256.txt
README.md
RELEASE_AUDIT.md
SHA256SUMS.txt
```
