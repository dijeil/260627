/* =====================================================================
   CSV 엑셀 한글 깨짐 자동 수정  (화면의 모든 [CSV] 버튼에 한 번에 적용)
   ---------------------------------------------------------------------
   문제: 화면에서 [CSV] 버튼으로 받은 파일을 더블클릭하면 엑셀에서 한글이 깨짐.
         원인은 파일 맨 앞에 'BOM'(엑셀에게 "이건 UTF-8이야"라고 알려 주는 표시)이 없어서.
         파이썬 쪽 utf-8-sig 와 같은 처리를 브라우저에서 해 줘야 한다.

   붙이는 법: 대시보드 HTML 의 <head> 안, 다른 스크립트보다 먼저 한 줄
       <script src="/static/excel_csv_fix.js"></script>
   → 기존 CSV 버튼 코드는 하나도 고칠 필요 없음.

   하는 일
     1) CSV 를 만들 때(Blob, data:text/csv 링크) 맨 앞에 BOM 을 자동으로 붙임
        → 더블클릭만으로 엑셀에서 한글이 정상으로 보임
     2) 종목코드처럼 앞자리가 0인 숫자(005930)는 ="005930" 으로 감싸서
        엑셀이 5930 으로 바꾸지 못하게 함 (끄려면 ExcelCsvFix.keepZeros = false)
   ===================================================================== */
(function () {
  "use strict";
  if (window.ExcelCsvFix) return;

  var BOM = "﻿";
  var api = window.ExcelCsvFix = { keepZeros: true, fixed: 0 };

  function isCsvType(t) { return /(^|\/|\b)(csv|comma-separated-values)\b|vnd\.ms-excel/i.test(t || ""); }

  // 따옴표를 지키며 CSV 를 칸 단위로 나눈다
  function parse(text, sep) {
    var rows = [], row = [], f = "", q = false, i = 0, c;
    for (; i < text.length; i++) {
      c = text[i];
      if (q) {
        if (c === '"') { if (text[i + 1] === '"') { f += '"'; i++; } else q = false; }
        else f += c;
      } else if (c === '"' && f === "") q = true;
      else if (c === sep) { row.push(f); f = ""; }
      else if (c === "\n" || c === "\r") {
        if (c === "\r" && text[i + 1] === "\n") i++;
        row.push(f); rows.push(row); row = []; f = "";
      } else f += c;
    }
    if (f !== "" || row.length) { row.push(f); rows.push(row); }
    return rows;
  }
  function quote(v, sep) { return /["\r\n]/.test(v) || v.indexOf(sep) >= 0 ? '"' + v.replace(/"/g, '""') + '"' : v; }

  function protectZeros(text) {
    if (!/(^|[,\t\n"])0\d/.test(text)) return text;            // 앞자리 0 숫자가 없으면 그대로
    var first = text.split(/\r?\n/, 1)[0];
    var sep = first.indexOf("\t") >= 0 && first.indexOf(",") < 0 ? "\t" : ",";
    var nl = text.indexOf("\r\n") >= 0 ? "\r\n" : "\n";
    var changed = false;
    var out = parse(text, sep).map(function (r) {
      return r.map(function (v) {
        if (/^0\d+$/.test(v)) { changed = true; return quote('="' + v + '"', sep); }   // 005930 → ="005930"
        return quote(v, sep);
      }).join(sep);
    }).join(nl);
    return changed ? out + (/\r?\n$/.test(text) ? nl : "") : text;
  }

  function fixText(s) {
    if (s.charCodeAt(0) === 0xFEFF) s = s.slice(1);
    if (api.keepZeros) s = protectZeros(s);
    api.fixed++;
    return BOM + s;
  }

  function hasBomBytes(p) {
    var u = p instanceof ArrayBuffer ? new Uint8Array(p) : ArrayBuffer.isView(p) ? new Uint8Array(p.buffer, p.byteOffset, p.byteLength) : null;
    return u && u.length >= 3 && u[0] === 0xEF && u[1] === 0xBB && u[2] === 0xBF;
  }

  function fixParts(parts) {
    var arr = Array.prototype.slice.call(parts);
    if (!arr.length) return arr;
    if (arr.every(function (p) { return typeof p === "string"; })) return [fixText(arr.join(""))];
    if (typeof arr[0] === "string") { if (arr[0].charCodeAt(0) !== 0xFEFF) arr.unshift(BOM); return arr; }
    if (!hasBomBytes(arr[0])) arr.unshift(BOM);                 // 바이트로 만든 CSV: BOM 만 앞에
    return arr;
  }

  /* 1) new Blob([...], {type:"text/csv"}) 가로채기 */
  var NativeBlob = window.Blob;
  function PatchedBlob(parts, opts) {
    if (opts && isCsvType(opts.type) && parts) {
      parts = fixParts(parts);
      opts = Object.assign({}, opts, { type: "text/csv;charset=utf-8" });
    }
    return new NativeBlob(parts || [], opts);
  }
  PatchedBlob.prototype = NativeBlob.prototype;
  try { Object.setPrototypeOf(PatchedBlob, NativeBlob); } catch (e) { /* 옛 브라우저 */ }
  window.Blob = PatchedBlob;

  /* 2) <a href="data:text/csv,..." download> 방식 가로채기 */
  function fixAnchor(a) {
    var h = a && a.getAttribute && a.getAttribute("href");
    if (!h || !/^data:(text\/csv|application\/vnd\.ms-excel)/i.test(h)) return;
    var comma = h.indexOf(","), meta = h.slice(5, comma), body = h.slice(comma + 1), text;
    try { text = /;base64/i.test(meta) ? decodeURIComponent(escape(atob(body))) : decodeURIComponent(body); }
    catch (e) { return; }
    a.setAttribute("href", URL.createObjectURL(new NativeBlob([fixText(text)], { type: "text/csv;charset=utf-8" })));
    if (!a.getAttribute("download")) a.setAttribute("download", "data.csv");
  }
  var nativeClick = HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click = function () { fixAnchor(this); return nativeClick.apply(this, arguments); };
  document.addEventListener("click", function (e) {
    var a = e.target && e.target.closest ? e.target.closest("a[href^='data:']") : null;
    if (a) fixAnchor(a);
  }, true);
})();
