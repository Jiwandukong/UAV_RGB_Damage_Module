# Geometry asset

Expected local file: `daecheong_dam_epsg5186_zup.obj`

- Original name: `dam - Cloud.obj`
- Size: `184,020,785` bytes
- SHA-256: `a7566c8d8f70de91db18c70ae5f404b0f7885e679a1027fd3e1936afd2d1e470`
- External coordinate contract: EPSG:5186 X/Y, metres, Z-up
- Bounds: `[242986.140625, 431066.09375, 32.6238327]` to `[243138.875, 431283.3125, 122.66383362]`

OBJ does not carry an embedded CRS. The contract above is project metadata and must remain with the file. The coordinate-less/Y-up GLB is intentionally unsupported.

After obtaining the verified OBJ, place it with:

```bash
cp "/path/to/dam - Cloud.obj" 01_RawData/geometry/daecheong_dam_epsg5186_zup.obj
sha256sum 01_RawData/geometry/daecheong_dam_epsg5186_zup.obj
```
