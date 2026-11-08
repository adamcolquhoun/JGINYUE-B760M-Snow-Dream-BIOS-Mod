# 378x100 24-bit BMP for the POST-screen logo slot: provided AMI logo, white bg -> black, black text -> white, red kept.
param([string]$Src, [string]$Out, [string]$Preview)
Add-Type -AssemblyName System.Drawing
$s = [Drawing.Bitmap]::new($Src)
$full = [Drawing.Bitmap]::new($s.Width, $s.Height, [Drawing.Imaging.PixelFormat]::Format24bppRgb)
for ($y = 0; $y -lt $s.Height; $y++) {
  for ($x = 0; $x -lt $s.Width; $x++) {
    $p = $s.GetPixel($x, $y)
    if (($p.R - $p.G) -gt 30) { $a = (255 - $p.G) / 255.0; $q = [Drawing.Color]::FromArgb(255, [int][Math]::Round(0xCC * $a), 0, 0) }
    else { $v = 255 - [int][Math]::Round(($p.R + $p.G + $p.B) / 3.0); $q = [Drawing.Color]::FromArgb(255, $v, $v, $v) }
    $full.SetPixel($x, $y, $q)
  }
}
$W = 378; $H = 100
$scale = [Math]::Min($W / $s.Width, $H / $s.Height)
$w = [int][Math]::Round($s.Width * $scale); $h = [int][Math]::Round($s.Height * $scale)
$c = [Drawing.Bitmap]::new($W, $H, [Drawing.Imaging.PixelFormat]::Format24bppRgb)
$g = [Drawing.Graphics]::FromImage($c); $g.Clear([Drawing.Color]::Black)
$g.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$g.PixelOffsetMode = [Drawing.Drawing2D.PixelOffsetMode]::HighQuality
$g.CompositingQuality = [Drawing.Drawing2D.CompositingQuality]::HighQuality
$ia = [Drawing.Imaging.ImageAttributes]::new(); $ia.SetWrapMode([Drawing.Drawing2D.WrapMode]::TileFlipXY)
$g.DrawImage($full, [Drawing.Rectangle]::new([int](($W - $w) / 2), [int](($H - $h) / 2), $w, $h), 0, 0, $s.Width, $s.Height, [Drawing.GraphicsUnit]::Pixel, $ia)
$g.Dispose()
$c.Save($Out, [Drawing.Imaging.ImageFormat]::Bmp)
$pv = [Drawing.Bitmap]::new($c, $W * 2, $H * 2); $pv.Save($Preview, [Drawing.Imaging.ImageFormat]::Png)
"scaled to ${w}x${h} in ${W}x${H}; $((Get-Item $Out).Length) bytes"
