"use strict";

const form = document.getElementById("aramaFormu");
const soruKutusu = document.getElementById("soru");
const araDugme = document.getElementById("araDugme");
const durumYazisi = document.getElementById("durumYazisi");
const hataKutusu = document.getElementById("hata");
const sonucAlani = document.getElementById("sonuc");
const yayinlarKutusu = document.getElementById("yayinlar");
const celiskiBolumu = document.getElementById("celiskiBolumu");
const celiskilerKutusu = document.getElementById("celiskiler");

// Durum -> CSS sınıfı (rozet ve kart rengi)
const DURUM_SINIFI = {
  "doğrulandı": "dogrulandi",
  "DOĞRULANAMADI": "dogrulanamadi",
  "ilgisiz": "ilgisiz",
  "özet yok": "ozet-yok",
  "analiz edilmedi": "edilmedi",
};
const durumSinifi = (durum) => DURUM_SINIFI[durum] || "diger";

// Ekranda gösterilen ad: "doğrulandı" bulgunun doğru olduğu sanılmasın
const DURUM_ETIKETI = { "doğrulandı": "dayanak doğrulandı" };
const durumEtiketi = (durum) => DURUM_ETIKETI[durum] || durum;
const DURUM_ACIKLAMASI = {
  "doğrulandı": "Modelin gösterdiği dayanak cümleler özette gerçekten var. " +
    "Bulgunun doğru ve soruyla ilgili olduğunu garanti etmez; elle kontrol et.",
  "DOĞRULANAMADI": "Model bulgu verdi ama geçerli bir dayanak cümle gösteremedi.",
};

// Güvenli eleman üretici: veri textContent ile yazılır, HTML olarak yorumlanmaz
function el(etiket, sinif, metin) {
  const e = document.createElement(etiket);
  if (sinif) e.className = sinif;
  if (metin !== undefined) e.textContent = metin;
  return e;
}

// Sadece http/https adresleri link olur (javascript: gibi adresler engellenir)
function guvenliLink(url) {
  return /^https?:\/\//i.test(url || "") ? url : "";
}

function baslikEleman(yayin) {
  const h = el("h3");
  const link = guvenliLink(yayin.link);
  if (link) {
    const a = el("a", "", yayin.baslik);
    a.href = link;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    h.append(a);
  } else {
    h.textContent = yayin.baslik;
  }
  return h;
}

function metaMetni(yayin) {
  const parcalar = [yayin.kaynaklar.join(", ")];
  if (yayin.doi) parcalar.push("DOI: " + yayin.doi);
  return parcalar.join(" · ");
}

// Bulgunun altındaki uyarılar (DOĞRULANAMADI açıklaması, rakam uyarısı, not)
function uyariEklemeleri(kart, yayin) {
  if (yayin.durum === "DOĞRULANAMADI") {
    kart.append(el("p", "uyari kirmizi",
      "Model bir bulgu verdi ama gösterdiği dayanak cümle numaraları geçersiz. Bu bulguya güvenme."));
  }
  if (yayin.rakam_uyarisi.length) {
    kart.append(el("p", "uyari",
      "Uyarı: Bulgudaki şu rakamlar dayanak cümlelerde yok: " + yayin.rakam_uyarisi.join(", ")));
  }
  if (yayin.not) kart.append(el("p", "uyari", yayin.not));
}

// ---- Parça 2: tıklayınca özet cümleleri ve dayanak vurgusu ----

// Yayının tüm özet cümleleri; dayanak olanlar vurgulu. Başta gizli.
function cumlePaneli(yayin) {
  const panel = el("div", "cumle-paneli");
  panel.hidden = true;
  const dayanakNolari = new Set(yayin.dayanak.map((d) => d.numara));
  const liste = el("ol", "cumleler");
  yayin.cumleler.forEach((cumle, i) => {
    const dayanakMi = dayanakNolari.has(i + 1);
    const li = el("li", dayanakMi ? "dayanak" : "", cumle);
    if (dayanakMi) li.title = "Dayanak cümle";
    liste.append(li);
  });
  panel.append(liste);
  return panel;
}

// Paneli aç/kapat; açılınca ilk dayanak cümleye kaydır
function panelDegistir(panel, ac, kaydir = true) {
  panel.hidden = ac === undefined ? !panel.hidden : !ac;
  if (panel.hidden) return;
  // Panelin kendi içinde ilk dayanak cümleyi ortaya getir (her panel için)
  const ilk = panel.querySelector(".dayanak");
  if (ilk) panel.scrollTop = ilk.offsetTop - (panel.clientHeight - ilk.offsetHeight) / 2;
  // Sayfayı da panele kaydır (yan yana açılırken sadece ilkine)
  if (kaydir) panel.scrollIntoView({ behavior: "smooth", block: "center" });
}

// İkincil düğme: metni açık/kapalı durumuna göre değişir
function panelDugmesi(acikMetin, kapaliMetin) {
  const d = el("button", "ikincil", kapaliMetin);
  d.type = "button";
  d.dataset.acik = acikMetin;
  d.dataset.kapali = kapaliMetin;
  return d;
}

// Tetikleyicileri (bulgu metni, düğme) panele bağlar; durum güncelleyiciyi döndürür
function baglaPanel(tetikleyiciler, panel) {
  const guncelle = () => {
    for (const t of tetikleyiciler) {
      t.setAttribute("aria-expanded", String(!panel.hidden));
      if (t.dataset.acik) t.textContent = panel.hidden ? t.dataset.kapali : t.dataset.acik;
    }
  };
  for (const t of tetikleyiciler) {
    const tikla = () => { panelDegistir(panel); guncelle(); };
    t.addEventListener("click", tikla);
    // Bulgu metni <p> olduğu için klavye (Enter/Boşluk) desteğini biz ekleriz
    if (t.tagName !== "BUTTON") {
      t.addEventListener("keydown", (olay) => {
        if (olay.key === "Enter" || olay.key === " ") { olay.preventDefault(); tikla(); }
      });
    }
  }
  guncelle();
  return guncelle;
}

// Bulgu paragrafını tıklanabilir yapar (klavyeyle de odaklanır)
function bulguEleman(yayin) {
  const p = el("p", "bulgu tikla", yayin.bulgu);
  p.tabIndex = 0;
  p.setAttribute("role", "button");
  p.title = "Özet cümlelerini göster / gizle";
  return p;
}

// ---- Parça 3: yazdırma ve indirme ----

// Sadece yazdırmada görünür: paneller kapalı olsa da PDF'te dayanak yer alsın
function yazdirDayanak(yayin) {
  const kutu = el("div", "yazdir-dayanak");
  for (const d of yayin.dayanak) {
    kutu.append(el("p", "", "Dayanak (" + d.numara + ". cümle): " + d.cumle));
  }
  return kutu;
}

function yayinKarti(yayin) {
  const kart = el("article", "kart");
  kart.dataset.durum = durumSinifi(yayin.durum);

  const ust = el("div", "kart-ust");
  const sol = el("div");
  sol.append(baslikEleman(yayin), el("p", "meta", metaMetni(yayin)));
  const rozet = el("span", "rozet " + durumSinifi(yayin.durum), durumEtiketi(yayin.durum));
  if (DURUM_ACIKLAMASI[yayin.durum]) rozet.title = DURUM_ACIKLAMASI[yayin.durum];
  ust.append(sol, rozet);
  kart.append(ust);

  // Özet cümleleri varsa ve analiz yapıldıysa panel + düğme eklenir
  const panelli = yayin.cumleler.length > 0 &&
    yayin.durum !== "analiz edilmedi" && yayin.durum !== "özet yok";
  const panel = panelli ? cumlePaneli(yayin) : null;
  const tetikleyiciler = [];

  if (yayin.bulgu) {
    const bulgu = panelli ? bulguEleman(yayin) : el("p", "bulgu", yayin.bulgu);
    if (panelli) tetikleyiciler.push(bulgu);
    kart.append(bulgu, yazdirDayanak(yayin));
  } else if (yayin.durum === "özet yok") {
    kart.append(el("p", "bos-not", "Özet yok, analiz yapılamadı."));
  } else if (yayin.durum === "analiz edilmedi") {
    // Rozet zaten söylüyor; metni tekrarlama, kartı kompakt tut
    kart.classList.add("sade");
  } else if (yayin.durum === "ilgisiz") {
    kart.append(el("p", "bos-not", "Bu yayın soruyla ilgisiz bulundu."));
  }
  uyariEklemeleri(kart, yayin);

  if (panel) {
    // Dayanak varsa düğme "Dayanak cümleleri", yoksa düz "Özet cümleleri"
    const ad = yayin.dayanak.length ? "Dayanak cümleleri" : "Özet cümleleri";
    const dugme = panelDugmesi(ad + " ▲ gizle", ad + " ▼ göster");
    tetikleyiciler.push(dugme);
    kart.append(dugme, panel);
    baglaPanel(tetikleyiciler, panel);
  }
  return kart;
}

function celiskiKarti(kayit, yayinlar, sira) {
  const kart = el("article", "kart celiski");
  kart.append(el("h3", "", "Çelişki " + sira));
  const kolonlar = el("div", "celiski-kolonlar");
  const paneller = [];
  const guncelleyiciler = [];
  for (const no of [kayit.a, kayit.b]) {
    const yayin = yayinlar.find((y) => y.no === no);
    const kolon = el("div", "kolon");
    const panel = cumlePaneli(yayin);
    const bulgu = bulguEleman(yayin);
    kolon.append(baslikEleman(yayin), bulgu, yazdirDayanak(yayin), panel);
    kolonlar.append(kolon);
    paneller.push(panel);
    // Kendi bulgusuna tıklayınca sadece o yayının paneli açılır
    guncelleyiciler.push(baglaPanel([bulgu], panel));
  }
  // Tek düğme iki panelin dayanaklarını yan yana açar/kapatır
  const dugme = panelDugmesi("Dayanak cümlelerini gizle ▲", "İki yayının dayanak cümlelerini yan yana göster ▼");
  dugme.addEventListener("click", () => {
    const ac = paneller.some((p) => p.hidden);
    // Ekran sadece ilk panele kayar; ikincisi yanında zaten görünür
    paneller.forEach((p, i) => panelDegistir(p, ac, i === 0));
    guncelleyiciler.forEach((g) => g());
    dugme.textContent = ac ? dugme.dataset.acik : dugme.dataset.kapali;
  });
  kart.append(kolonlar, dugme);
  if (kayit.aciklama) kart.append(el("p", "aciklama", kayit.aciklama));
  return kart;
}

// Özet satırı: "10 yayın" + her durum için renkli bir çip
function ozetCipleri(veri) {
  const sayim = {};
  for (const y of veri.yayinlar) sayim[y.durum] = (sayim[y.durum] || 0) + 1;
  const cipler = [el("span", "cip toplam", veri.yayinlar.length + " yayın")];
  for (const [durum, adet] of Object.entries(sayim)) {
    cipler.push(el("span", "cip " + durumSinifi(durum), adet + " " + durumEtiketi(durum)));
  }
  return cipler;
}

// Bulgusu olanlar üstte; ilgisizler kapalı bir başlıkta; analiz edilmeyenler en altta
function yayinListesi(yayinlar) {
  const ilgisiz = yayinlar.filter((y) => y.durum === "ilgisiz");
  const analizli = yayinlar.filter((y) => y.durum !== "analiz edilmedi" && y.durum !== "ilgisiz");
  const sade = yayinlar.filter((y) => y.durum === "analiz edilmedi");
  const ogeler = analizli.map(yayinKarti);
  if (ilgisiz.length) {
    // <details>: tarayıcının hazır aç/kapa öğesi, JavaScript gerektirmez
    const grup = el("details", "ilgisiz-grup");
    grup.append(el("summary", "", "İlgisiz bulundu (" + ilgisiz.length + ")"));
    for (const y of ilgisiz) {
      const kart = yayinKarti(y);
      kart.classList.add("sade");
      // "Bu yayın soruyla ilgisiz" cümlesi başlık zaten söylüyor
      kart.querySelector(".bos-not")?.remove();
      grup.append(kart);
    }
    ogeler.push(grup);
  }
  if (sade.length) {
    ogeler.push(el("h3", "grup-baslik", "Diğer yayınlar · analiz edilmedi (" + sade.length + ")"));
    ogeler.push(...sade.map(yayinKarti));
  }
  return ogeler;
}

// Son gelen sonuç; "Markdown indir" bunu kullanır (yeni arama yapılmaz)
let sonSonuc = null;

// Analiz edilenler arasında soruyla ilgili (bulgusu olan) hiç yayın yok mu?
// İlgisiz ya da model hatası fark etmez: ilgili yoksa kart gösterilmez.
function hicIlgiliYokMu(yayinlar) {
  const analizEdilen = yayinlar.filter(
    (y) => y.durum !== "analiz edilmedi" && y.durum !== "özet yok");
  return analizEdilen.length > 0 && !analizEdilen.some(
    (y) => y.durum === "doğrulandı" || y.durum === "DOĞRULANAMADI");
}

const ILGILI_YOK_MESAJI =
  "Soruyla ilgili yayın bulunamadı. Soruyu İngilizce ve daha açık yazmayı dene.";

// Uyarı kutusu bir kez oluşturulur, özet satırının hemen altına konur
const ilgisizUyari = el("p", "uyari", ILGILI_YOK_MESAJI);
ilgisizUyari.hidden = true;
document.getElementById("sonucOzet").after(ilgisizUyari);

function sonucuGoster(veri) {
  sonSonuc = veri;
  sonucAlani.hidden = false;
  document.getElementById("sonucBaslik").textContent = "Sonuçlar: " + veri.soru;
  document.getElementById("sonucOzet").replaceChildren(...ozetCipleri(veri));
  // Sunucu "araştırma sorusu değil" dediyse arama hiç yapılmadı, özet satırı da yok
  const reddedildi = Boolean(veri.uyari);
  document.getElementById("sonucOzet").hidden = reddedildi;
  const hepsiIlgisiz = reddedildi || hicIlgiliYokMu(veri.yayinlar);
  ilgisizUyari.textContent = veri.uyari || ILGILI_YOK_MESAJI;
  ilgisizUyari.hidden = !hepsiIlgisiz;
  // Hepsi ilgisizse kartlar, indirme düğmeleri ve alt not gösterilmez
  yayinlarKutusu.hidden = hepsiIlgisiz;
  sonucAlani.querySelector(".arac-cubugu").hidden = hepsiIlgisiz;
  sonucAlani.querySelector(".not").hidden = hepsiIlgisiz;

  yayinlarKutusu.replaceChildren(...yayinListesi(veri.yayinlar));

  celiskilerKutusu.replaceChildren();
  celiskiBolumu.hidden = !veri.celiskiler || hepsiIlgisiz;
  if (veri.celiskiler) {
    if (veri.celiskiler.liste.length === 0) {
      celiskilerKutusu.append(el("p", "bos-not", veri.celiskiler.mesaj));
    }
    veri.celiskiler.liste.forEach((kayit, i) => {
      celiskilerKutusu.append(celiskiKarti(kayit, veri.yayinlar, i + 1));
    });
  }
}

function hataGoster(mesaj) {
  hataKutusu.textContent = mesaj;
  hataKutusu.hidden = false;
}

// PDF: tarayıcının yazdırma penceresi açılır, "PDF olarak kaydet" seçilir
document.getElementById("pdfDugme").addEventListener("click", () => window.print());

// Markdown: render_report çıktısı rapor-YYYY-AA-GG.md olarak iner
document.getElementById("mdDugme").addEventListener("click", () => {
  if (!sonSonuc || !sonSonuc.rapor_md) return;
  const t = new Date();
  const iki = (n) => String(n).padStart(2, "0");
  const tarih = t.getFullYear() + "-" + iki(t.getMonth() + 1) + "-" + iki(t.getDate());
  const blob = new Blob([sonSonuc.rapor_md], { type: "text/markdown;charset=utf-8" });
  const adres = URL.createObjectURL(blob);
  const a = el("a");
  a.href = adres;
  a.download = "rapor-" + tarih + ".md";
  document.body.append(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(adres);
});

form.addEventListener("submit", async (olay) => {
  // Sayfanın yenilenmesini engelle (Laravel'deki normal form post'u yerine fetch)
  olay.preventDefault();
  const kaynak = form.querySelector('input[name="kaynak"]:checked').value;

  // Arama sürerken düğme kilitli, bekleme yazısı görünür
  araDugme.disabled = true;
  araDugme.setAttribute("aria-busy", "true");
  durumYazisi.textContent = "Aranıyor, lütfen bekle...";
  // Sonuç gelene kadar yer tutucu iskelet kartlar
  document.getElementById("yukleniyor").hidden = false;
  hataKutusu.hidden = true;
  sonucAlani.hidden = true;

  try {
    const yanit = await fetch("/ara", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sorgu: soruKutusu.value, kaynak }),
    });
    const veri = await yanit.json();
    if (veri.hata) {
      hataGoster(veri.hata);
    } else {
      sonucuGoster(veri);
    }
  } catch (hata) {
    hataGoster("Sunucuya ulaşılamadı. py app.py hâlâ çalışıyor mu?");
  } finally {
    // Ne olursa olsun düğme tekrar açılır
    araDugme.disabled = false;
    araDugme.removeAttribute("aria-busy");
    durumYazisi.textContent = "";
    document.getElementById("yukleniyor").hidden = true;
  }
});
