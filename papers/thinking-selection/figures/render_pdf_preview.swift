// Render final PDFs through macOS PDFKit/Quartz for visual artifact review.
// Only command-line PDF paths are opened. No experiment artifacts are read.
import Foundation
import PDFKit
import AppKit

guard CommandLine.arguments.count == 3 else {
    fatalError("Usage: swift render_pdf_preview.swift input.pdf output.png")
}
let input = URL(fileURLWithPath: CommandLine.arguments[1])
let output = URL(fileURLWithPath: CommandLine.arguments[2])
guard let doc = PDFDocument(url: input), doc.pageCount == 1,
      let page = doc.page(at: 0), let pageRef = page.pageRef else {
    fatalError("Expected one readable figure page")
}
let bounds = page.bounds(for: .mediaBox)
let scale: CGFloat = 2
let width = Int(bounds.width * scale)
let height = Int(bounds.height * scale)
guard let ctx = CGContext(data: nil, width: width, height: height,
                          bitsPerComponent: 8, bytesPerRow: width * 4,
                          space: CGColorSpaceCreateDeviceRGB(),
                          bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else {
    fatalError("Cannot create bitmap context")
}
ctx.setFillColor(CGColor(gray: 1, alpha: 1))
ctx.fill(CGRect(x: 0, y: 0, width: width, height: height))
ctx.scaleBy(x: scale, y: scale)
ctx.translateBy(x: -bounds.minX, y: -bounds.minY)
ctx.drawPDFPage(pageRef)
guard let image = ctx.makeImage(),
      let png = NSBitmapImageRep(cgImage: image).representation(using: .png, properties: [:]) else {
    fatalError("Cannot encode preview")
}
try png.write(to: output)
let text = page.string ?? ""
print("PDF page: \(bounds.width) x \(bounds.height) pt; preview: \(width) x \(height); extracted text characters: \(text.count)")
