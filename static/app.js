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

function yayinKarti(yayin) {
  const kart = el("article", "kart");
  kart.dataset.durum = durumSinifi(yayin.durum);

  const ust = el("div", "kart-ust");
  const sol = el("div");
  sol.append(baslikEleman(yayin), el("p", "meta", metaMetni(yayin)));
  ust.append(sol, el("span", "rozet " + durumSinifi(yayin.durum), yayin.durum));
  kart.append(ust);

  if (yayin.bulgu) {
    kart.append(el("p", "bulgu", yayin.bulgu));
  } else if (yayin.durum === "özet yok") {
    kart.append(el("p", "bos-not", "Özet yok, analiz yapılamadı."));
  } else if (yayin.durum === "analiz edilmedi") {
    // Rozet zaten söylüyor; metni tekrarlama, kartı kompakt tut
    kart.classList.add("sade");
  } else if (yayin.durum === "ilgisiz") {
    kart.append(el("p", "bos-not", "Bu yayın soruyla ilgisiz bulundu."));
  }
  uyariEklemeleri(kart, yayin);
  return kart;
}

function celiskiKarti(kayit, yayinlar, sira) {
  const kart = el("article", "kart celiski");
  kart.append(el("h3", "", "Çelişki " + sira));
  const kolonlar = el("div", "celiski-kolonlar");
  for (const no of [kayit.a, kayit.b]) {
    const yayin = yayinlar.find((y) => y.no === no);
    const kolon = el("div", "kolon");
    kolon.append(baslikEleman(yayin), el("p", "bulgu", yayin.bulgu));
    kolonlar.append(kolon);
  }
  kart.append(kolonlar);
  if (kayit.aciklama) kart.append(el("p", "aciklama", kayit.aciklama));
  return kart;
}

function ozetMetni(veri) {
  const sayim = {};
  for (const y of veri.yayinlar) sayim[y.durum] = (sayim[y.durum] || 0) + 1;
  const parcalar = Object.entries(sayim).map(([durum, adet]) => adet + " " + durum);
  return veri.yayinlar.length + " yayın: " + parcalar.join(", ");
}

function sonucuGoster(veri) {
  sonucAlani.hidden = false;
  document.getElementById("sonucBaslik").textContent = "Sonuçlar: " + veri.soru;
  document.getElementById("sonucOzet").textContent = ozetMetni(veri);

  yayinlarKutusu.replaceChildren(...veri.yayinlar.map(yayinKarti));

  celiskilerKutusu.replaceChildren();
  celiskiBolumu.hidden = !veri.celiskiler;
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

form.addEventListener("submit", async (olay) => {
  // Sayfanın yenilenmesini engelle (Laravel'deki normal form post'u yerine fetch)
  olay.preventDefault();
  const kaynak = form.querySelector('input[name="kaynak"]:checked').value;

  // Arama sürerken düğme kilitli, bekleme yazısı görünür
  araDugme.disabled = true;
  durumYazisi.textContent = "Aranıyor, lütfen bekle...";
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
    durumYazisi.textContent = "";
  }
});
