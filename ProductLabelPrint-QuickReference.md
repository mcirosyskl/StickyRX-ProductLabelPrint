# ProductLabelPrint — Quick Reference

## Setup (one time, per workstation)

1. **Set the printer's default size to 4x6.** Windows Settings ▸ Printers & Scanners ▸ your printer ▸ Printing Preferences ▸ Paper size ▸ select or create 4x6 ▸ Set as Default.
2. **Confirm the exact printer name.** Open ProductLabelPrint ▸ cog icon ▸ Setup Config ▸ "Printer name" must match Windows exactly (Settings ▸ Printers & Scanners) ▸ Save.

## Daily Operation

1. Open **ProductLabelPrint** and click **SCAN / PRINT LABEL**.
2. **Scan the Kanban card barcode.**
3. **Confirm the quantity** (or type a different number), then press **Enter** or click **Print**.

## Good to Know

- **Leave Affinity Designer open** if it appears on screen — don't close it between scans. Keeping it running lets future labels reuse the same open window instead of starting fresh each time, which is faster.
- **The first scan of a new (or newly edited) product briefly opens Affinity** on screen to build a print file. This is normal — you'll see it happen once per product.
- **Every scan after that is fast.** Once a product's print file has been built, re-scanning that same barcode skips the Affinity step entirely and reuses the saved file — no on-screen activity, straight to printing.
