import os, shutil, random
random.seed(42)
base_dir = "dataset" 

# Path Sumber 
img_src  = os.path.join(base_dir, "train/images") 
lbl_src  = os.path.join(base_dir, "train/labels")


img_val  = os.path.join(base_dir, "val/images")
lbl_val  = os.path.join(base_dir, "val/labels")
img_test = os.path.join(base_dir, "test/images")
lbl_test = os.path.join(base_dir, "test/labels")

# Buat folder jika belum ada
os.makedirs(img_val,  exist_ok=True)
os.makedirs(lbl_val,  exist_ok=True)
os.makedirs(img_test, exist_ok=True)
os.makedirs(lbl_test, exist_ok=True)

# Ambil semua file gambar
if os.path.exists(img_src):
    images = [f for f in os.listdir(img_src) if f.lower().endswith((".jpg", ".png", ".jpeg"))]
    random.shuffle(images)

    # Hitung proporsi (80% Train, 10% Val, 10% Test)
    val_count  = int(len(images) * 0.10)
    test_count = int(len(images) * 0.10)

    val_images  = images[:val_count]
    test_images = images[val_count:val_count + test_count]

    def move_files(file_list, src_img, src_lbl, dst_img, dst_lbl):
        for fname in file_list:
            # Pindah gambar
            shutil.move(os.path.join(src_img, fname), os.path.join(dst_img, fname))
            # Pindah label txt
            label = os.path.splitext(fname)[0] + ".txt"
            lbl_path = os.path.join(src_lbl, label)
            if os.path.exists(lbl_path):
                shutil.move(lbl_path, os.path.join(dst_lbl, label))

    # Eksekusi pindah file
    move_files(val_images,  img_src, lbl_src, img_val,  lbl_val)
    move_files(test_images, img_src, lbl_src, img_test, lbl_test)

    train_count = len(images) - val_count - test_count
    print(f"Dataset berhasil dibagi!")
    print(f"Train : {train_count}")
    print(f"Val   : {val_count}")
    print(f"Test  : {test_count}")
else:
    print(f"ERROR: Folder {img_src} tidak ditemukan. Cek lagi nama foldernya!")