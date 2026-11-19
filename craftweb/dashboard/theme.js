try {
  var d = document.documentElement;
  var t = localStorage.getItem("cw.theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  var l = localStorage.getItem("cw.lang") || "ar";
  d.dataset.theme = t; d.lang = l; d.dir = l === "ar" ? "rtl" : "ltr";
} catch (e) {}
