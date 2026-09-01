(function(){
  'use strict';

  const pages=window.VITO_I18N&&window.VITO_I18N.pages;
  if(!pages)return;
  const originalPages=JSON.parse(JSON.stringify(pages));
  const preservedCitations={};
  Object.entries(pages).forEach(([pageKey,strings])=>{
    preservedCitations[pageKey]={};
    Object.entries(strings).forEach(([key,value])=>{
      const citations=String(value).match(/<sup\b[\s\S]*?<\/sup>/g);
      if(citations)preservedCitations[pageKey][key]=citations.join('');
    });
  });

  function assign(pageKey,strings){
    if(pages[pageKey])Object.assign(pages[pageKey],strings);
  }

  function replaceText(pageKey,key,value){
    const page=pages[pageKey];
    if(!page)return;
    const citations=(page[key]||'').match(/<sup\b[\s\S]*?<\/sup>/g)||[];
    page[key]=value+(value.includes('<sup')?'':citations.join(''));
  }

  assign('home',{
    'home-007':'Venture capitalist & builder · Asia Tenggara',
    'home-160':'Doa, harapan, dan dukungan',
    'home-161':'Apakah ada doa,<br/>harapan, atau pesan dukungan untuk saya?',
    'home-162':'Bagikan melalui Papan Doa & Harapan saya. Anda dapat menulis secara anonim, memberikan semangat, atau menceritakan harapan yang sedang Anda perjuangkan.',
    'home-166':'Catatan lapangan',
    'home-167':'Karya di balik layar.',
    'home-168':'Dunia venture tidak hanya berlangsung di depan layar. Ada proses sourcing, penjurian, mentoring, dan uji tuntas di ruang diskusi, di atas panggung, hingga langsung di lapangan, dari Indonesia dan Singapura hingga berbagai tempat lainnya. Klik setiap foto untuk membaca ceritanya dan memperbesar gambar.',
    'home-169':'Baca catatan ↗',
    'home-170':'Lihat semua catatan <span aria-hidden="true">↗</span>',
    'home-171':'Tulis di sini ↗',
    'home-172':'Kirim email',
    'home-173':'AI & Asia Tenggara · 29 Agustus 2026 · 23 menit membaca',
    'home-174':'Membangun Venture Iklim · 26 Agustus 2026 · 10 menit membaca',
    'home-175':'AI & Asia Tenggara · 10 Agustus 2026 · 13 menit membaca',
    'home-176':'Laporan lengkap ↗',
    'home-178':'← Sebelumnya',
    'home-179':'Berikutnya →',
    'home-180':'Untuk founder',
    'home-181':'Dibangun di New Energy Nexus Ventures · Demo publik dengan data tersanitasi',
    'home-182':'Internal · New Energy Nexus Ventures',
    'home-183':'Riset · New Energy Nexus Ventures',
    'home-184':'Riset · Living Lab Ventures',
    'home-185':'Buka laporan lengkap (PDF) ↗',
    'home-186':'Buka hasil lengkap (PDF) ↗',
    'home-187':'Baca paper di IEEE ↗'
  });

  assign('home',{
    'home-023':'Co-pilot penggalangan dana untuk founder Asia Tenggara: evaluasi deck, latih pitch bersama investor AI, temukan investor yang aktif di kawasan, dan pantau setiap percakapan hingga term sheet. Mulai presentasi bernarasi dengan <b>► Narasi</b>. Slide akan mengikuti audio.',
    'home-030':'Saya merancang dan membangun platform intelligence yang mengubah data counterparty yang terpencar menjadi jaringan LP, co-investor, fund, perusahaan portofolio, dan pipeline startup yang dapat ditelusuri. Platform ini membantu menemukan jalur perkenalan yang bernilai tinggi, celah hubungan, serta peluang untuk penggalangan dana, deal sourcing, co-investment, dan dukungan portofolio. Tampilan di bawah adalah replika publik dengan skala yang disederhanakan.',
    'home-037':'Meja penyaringan investasi berbantuan AI untuk fund teknologi iklim. Sistem ini mengevaluasi deck, menguji kesesuaiannya dengan tesis investasi, memodelkan skenario exit, menyusun memo, dan memantau pipeline dari peluang masuk hingga komite investasi.',
    'home-038':'Penyaringan deck',
    'home-039':'Mesin penilaian',
    'home-040':'Kesesuaian tesis',
    'home-041':'Exit & imbal hasil',
    'home-042':'Memo investasi',
    'home-043':'Pipeline / Kanban',
    'home-044':'Riset State of the Industry yang saya susun di New Energy Nexus Ventures menjelaskan mengapa Asia Tenggara menjadi salah satu frontier berikutnya bagi solusi iklim. Hingga <b>11% PDB kawasan</b> berisiko hilang pada 2100, sementara kerugian akibat iklim telah mencapai sekitar US$100 miliar per tahun. Di sisi lain, kapitalisasi pasar ekonomi hijau mencapai sekitar <b>US$8 triliun</b>, meski kesenjangan pendanaannya masih bernilai triliunan dolar. Laporan ini memetakan seluruh lapisan solusi, mulai dari mitigasi, adaptasi dan ketahanan, hingga perangkat lunak AI serta MRV. Setiap negara membawa kekuatan yang saling melengkapi: modal di Singapura, permintaan di Indonesia, kapasitas manufaktur di Vietnam, dan pengalaman membangun ketahanan di Filipina. Mulai presentasi bernarasi dengan <b>► Narasi</b>.',
    'home-045':'Data urgensi iklim',
    'home-046':'Peta solusi',
    'home-047':'Kesenjangan pendanaan',
    'home-048':'Analisis setiap negara',
    'home-049':'Sinyal disrupsi 2026',
    'home-050':'Publikasi riset yang saya tulis bersama di Living Lab Ventures memetakan kondisi setelah awal 2025 yang penuh tekanan. Nilai transaksi turun <b>59%</b> di Asia Tenggara dan <b>85%</b> di Indonesia dari kuartal keempat 2024 hingga kuartal pertama 2025, mencapai titik terendah sejak 2022. Laporan ini membahas kenaikan healthcare menjadi sektor dengan pendanaan terbesar kedua di kawasan, momentum manufaktur dan nearshoring ketika jalur perdagangan global berubah, serta peluang investasi yang muncul dari agenda ekonomi pemerintahan Prabowo. Partner kami, Bayu Seto, mempresentasikan laporan yang saya tulis bersama Sari Ichtiari dan Fadhlan Fariz. Mulai presentasi bernarasi dengan <b>► Narasi</b>.',
    'home-051':'Data nilai transaksi venture',
    'home-052':'Momentum healthcare',
    'home-053':'Manufaktur & nearshoring',
    'home-054':'Peluang kebijakan',
    'home-055':'Lima sektor dalam pantauan'
  });

  assign('home',{
    'home-118':'Dua asesmen terstandar yang saya ikuti pada November 2025, ditampilkan apa adanya beserta kekuatan dan area yang perlu saya waspadai. Bagian ini ditujukan bagi recruiter, founder, dan sesama investor yang ingin memahami cara saya berpikir dan bekerja sebelum kita bertemu. Kedua laporan lengkap dapat dibuka di bawah.',
    'home-119':'Bagian 01 · Entrepreneurial DNA',
    'home-120':'Arketipe',
    'home-121':'Arketipe: The Achiever',
    'home-122':'“Seorang Achiever pada dasarnya <em>menolak kalah</em> dan akan bekerja keras untuk memastikan hal itu tidak terjadi.”',
    'home-123':'Berkinerja terbaik dalam situasi yang menantang dan penuh tekanan',
    'home-124':'Gigih dan tidak takut menghadapi kegagalan',
    'home-125':'Mampu mendorong dan memotivasi orang lain',
    'home-126':'Nyaman mengambil risiko yang terukur dan mendorong batas kemungkinan',
    'home-127':'Kekuatan utama · persentil',
    'home-128':'Sangat tinggi ×3',
    'home-129':'Menetapkan sasaran ambisius, melampaui ekspektasi, dan cepat menguasai kemampuan baru. Hal yang perlu dijaga adalah risiko kelelahan, sehingga ritme pencapaian harus diimbangi dengan pemulihan yang disengaja.',
    'home-130':'Cepat menyesuaikan strategi ketika menerima informasi baru dan nyaman mengelola beberapa alur kerja sekaligus. Kekuatan ini paling efektif ketika diimbangi dengan disiplin untuk bertahan pada satu komitmen hingga benar-benar selesai.',
    'home-131':'Terdorong oleh eksplorasi dan eksperimen, nyaman dengan risiko, gagasan baru, dan tantangan terhadap status quo. Keseimbangannya datang dari menggabungkan kebaruan dengan metode yang telah terbukti.',
    'home-132':'<b>Mengapa ini masuk akal</b> Jejaknya terlihat sejak seorang anak dari Kediri belajar di ITB, lalu menguji diri dalam ekosistem inovasi Singapura dan Jepang melalui NUS Overseas Colleges serta Social Innovator Hub di Tohoku University. Perjalanan itu berlanjut dari tesis yang diterbitkan IEEE hingga menjadi juara kedua global di Hack The Globe oleh BCG. <b>Apa artinya dalam bekerja</b> Saya membawa dorongan layaknya founder ke sisi investor. Di Living Lab Ventures, saya berkembang dari intern menjadi anggota tim penuh waktu termuda sambil menjalankan proses investasi dari awal hingga selesai.',
    'home-133':'Bagian 02 · Big Five Personality Test',
    'home-134':'Radar profil',
    'home-135':'IPIP-NEO-120 · sumber terbuka',
    'home-136':'Domain · skor / 120',
    'home-137':'Klasifikasi dalam laporan',
    'home-138':'Keterbukaan<span>Tinggi</span>',
    'home-139':'Kedisiplinan<span>Tinggi</span>',
    'home-140':'Ekstraversi<span>Rendah · tetap asertif</span>',
    'home-141':'Neurotisisme<span>Rendah</span>',
    'home-142':'Keramahan<span>Rendah · objektif</span>',
    'home-143':'Facet tertinggi (dari 20)',
    'home-144':'Efikasi diri <b>20</b>',
    'home-145':'Pencarian kegembiraan <b>20</b>',
    'home-146':'Petualangan <b>19</b>',
    'home-147':'Dorongan berprestasi <b>19</b>',
    'home-148':'Imajinasi <b>17</b>',
    'home-149':'Intelektualitas <b>16</b>',
    'home-150':'Rasa tanggung jawab <b>16</b>',
    'home-151':'Ketegasan <b>13 · tinggi</b>',
    'home-152':'Facet terendah yang perlu disadari',
    'home-153':'Kesenangan bersosialisasi <b>5</b>',
    'home-154':'Kepercayaan <b>7</b>',
    'home-155':'Kehati-hatian <b>8</b>',
    'home-156':'Keteraturan <b>9</b>',
    'home-157':'<b>Mengapa ini relevan</b> Kombinasi keterbukaan dan kedisiplinan yang tinggi dengan keramahan yang lebih rendah sesuai dengan tuntutan pekerjaan saya. Saya cukup ingin tahu untuk mendalami tesis baru, cukup disiplin untuk menuntaskan model, dan cukup objektif untuk mengatakan tidak ketika bukti tidak mendukung keputusan. Pola ini mendasari ketekunan dalam menjalankan transaksi di Living Lab Ventures dan membangun kerangka penyaringan di New Energy Nexus Ventures. <b>Apa artinya dalam bekerja</b> Rekan kerja dapat mengharapkan komunikasi yang langsung, keputusan berbasis bukti, dan ketenangan dalam situasi berisiko tinggi, mulai dari komite investasi hingga panggung penjurian.',
    'home-158':'Kesimpulan',
    'home-159':'Saya adalah <em>operator berorientasi pencapaian yang cepat beradaptasi</em>: selalu ingin tahu, tenang di bawah tekanan, dan objektif dalam menilai bukti. Berikan saya sasaran ambisius di pasar yang penuh ketidakpastian, dan saya akan bekerja keras, belajar lebih cepat, serta terus memperbaiki pendekatan hingga sasaran itu tercapai.'
  });

  assign('notes',{
    'notes-001':'Karya',
    'notes-002':'Pengalaman',
    'notes-003':'Latar belakang',
    'notes-004':'Catatan',
    'notes-005':'Kepribadian',
    'notes-006':'Perjalanan',
    'notes-007':'Catatan',
    'notes-008':'Gagasan dari persimpangan modal dan teknologi.',
    'notes-009':'Catatan lapangan, perspektif investasi, dan esai tentang Asia Tenggara, iklim, kecerdasan buatan, serta upaya membangun ekosistem venture yang lebih baik.',
    'notes-010':'Tulisan terbaru',
    'notes-011':'3 catatan',
    'notes-012':'AI & Asia Tenggara',
    'notes-013':'29 Agustus 2026',
    'notes-014':'23 menit membaca',
    'notes-015':'Dapatkah Pekerja Asia Tenggara Tetap Relevan di Era AI?',
    'notes-016':'Asia Tenggara memasuki era AI dengan tenaga kerja yang sebagian besar berada di sektor informal. Agar tetap relevan, kawasan ini membutuhkan lebih dari keterampilan teknis. Produktivitas yang lebih tinggi, institusi yang lebih kuat, dan aturan pembagian manfaat yang lebih adil sama pentingnya.',
    'notes-017':'Membangun Venture Iklim',
    'notes-018':'26 Agustus 2026',
    'notes-019':'10 menit membaca',
    'notes-020':'Dari Bukti Lapangan Menuju Uji Coba yang Terukur',
    'notes-021':'Pelajaran dari mendampingi tim NomaTech Challenge untuk COP17 dalam mengubah gagasan iklim menjadi uji coba yang kredibel, model bisnis yang kuat, dan narasi venture berbasis bukti.',
    'notes-022':'AI & Asia Tenggara',
    'notes-023':'10 Agustus 2026',
    'notes-024':'13 menit membaca',
    'notes-025':'Di Mana Asia Tenggara Dapat Unggul dalam Gelombang AI?',
    'notes-026':'Modal global semakin terkonsentrasi pada kecerdasan buatan. Namun, Asia Tenggara tidak harus bersaing langsung dalam pengembangan model AI terdepan. Peluang terbesarnya mungkin terletak pada penerapan AI untuk alur kerja lokal, serta pembangunan infrastruktur, perangkat keras, dan distribusi yang membuat teknologi ini berguna dalam skala besar.',
    'notes-027':'Portofolio',
    'notes-029':'Kontak',
    'notes-030':'Baca catatan ↗'
  });

  assign('sea-workers-ai',{
    'sea-workers-ai-006':'Foto',
    'sea-workers-ai-008':'← Semua catatan',
    'sea-workers-ai-009':'AI & Asia Tenggara',
    'sea-workers-ai-010':'Dapatkah Pekerja Asia Tenggara Tetap Relevan di Era AI?',
    'sea-workers-ai-011':'Asia Tenggara memasuki era AI dengan tenaga kerja yang sebagian besar berada di sektor informal. Agar tetap relevan, kawasan ini membutuhkan lebih dari keterampilan teknis. Produktivitas yang lebih tinggi, institusi yang lebih kuat, dan aturan pembagian manfaat yang lebih adil sama pentingnya.',
    'sea-workers-ai-012':'Oleh Vito Christian Samudra',
    'sea-workers-ai-013':'29 Agustus 2026',
    'sea-workers-ai-014':'23 menit membaca',
    'sea-workers-ai-015':'Kecerdasan buatan',
    'sea-workers-ai-016':'Masa depan dunia kerja',
    'sea-workers-ai-017':'Asia Tenggara',
    'sea-workers-ai-018':'Ekonomi informal',
    'sea-workers-ai-019':'Asia Tenggara memasuki era AI dengan tenaga kerja yang sebagian besar berada di sektor informal. Pertanyaan utamanya adalah apakah teknologi dapat memperkuat pekerja lebih cepat daripada mengurangi kebutuhan terhadap tenaga kerja.',
    'sea-workers-ai-020':'Asia Tenggara memasuki era AI dengan tenaga kerja yang sebagian besar berada di sektor informal',
    'sea-workers-ai-021':'Sebagian besar pembahasan tentang kecerdasan buatan dan ketenagakerjaan dimulai dari dunia kerja formal, seperti kantor, pabrik, jasa profesional, dan pekerjaan berbasis pengetahuan. Asia Tenggara memasuki era AI dari titik awal yang sangat berbeda.',
    'sea-workers-ai-023':'Pekerjaan informal tidak selalu berarti tidak produktif atau berketerampilan rendah. Istilah ini menjelaskan kondisi seseorang bekerja, termasuk akses terhadap kontrak, perlindungan tenaga kerja, dan jaminan sosial. Ekonomi informal Asia Tenggara mencakup petani, pedagang, pengemudi, pekerja konstruksi, produsen rumahan, pemilik usaha kecil, serta berbagai bentuk pekerjaan mandiri. Mereka telah menciptakan nilai ekonomi dan sosial yang besar, tetapi sering bekerja dengan akses terbatas terhadap modal, teknologi, informasi, pelatihan, logistik, dan pasar yang lebih luas.',
    'sea-workers-ai-024':'Kondisi ini mengubah pertanyaan utama tentang AI di kawasan. Negara maju terutama bertanya apakah AI akan menggantikan pekerja dalam pekerjaan formal yang sudah ada. Asia Tenggara juga perlu bertanya apakah AI dapat membuat tenaga kerjanya lebih produktif. Petani dapat menggunakan informasi cuaca, pembiayaan, dan pasar digital untuk meningkatkan hasil panen serta mengurangi pemborosan. Pedagang kecil dapat memperbaiki pengelolaan persediaan, penetapan harga, dan jangkauan pelanggan. Desainer atau developer dapat menggunakan AI untuk melayani lebih banyak klien di pasar internasional. Dalam setiap contoh, pekerja yang sama dapat menciptakan nilai ekonomi yang lebih besar.',
    'sea-workers-ai-025':'Peluang ini juga mengandung sebuah paradoks. Ketika teknologi memungkinkan satu orang menghasilkan sesuatu yang sebelumnya membutuhkan beberapa pekerja, produktivitas dapat meningkat sementara permintaan terhadap tenaga kerja menurun. Pekerja yang mengadopsi teknologi dapat menjadi lebih bernilai, tetapi pekerja lain mungkin menghadapi kesempatan yang semakin sedikit. Tantangan Asia Tenggara bukan sekadar menghitung berapa banyak pekerjaan yang mungkin digantikan AI. Kawasan ini perlu memastikan bahwa produktivitas berbasis AI menciptakan tambahan output, permintaan, ekspor, dan pendapatan yang cukup untuk menjaga inklusivitas ekonomi di wilayah dengan tenaga kerja melimpah.',
    'sea-workers-ai-026':'Pekerja informal membutuhkan akses terhadap teknologi, modal, keterampilan, data, dan pasar agar dapat menikmati manfaat tersebut. Pemerintah, lembaga keuangan, perusahaan teknologi, dan bisnis besar dapat membantu menyediakan infrastruktur produktif itu. Tujuannya tidak harus memindahkan setiap pekerja informal ke pekerjaan formal konvensional dalam waktu singkat. Langkah awalnya dapat berupa peningkatan produktivitas, pendapatan, dan daya tawar pekerja yang telah menjadi fondasi perekonomian kawasan.',
    'sea-workers-ai-027':'<p>Dapatkah Asia Tenggara memperluas manfaat produktivitas dan menciptakan permintaan baru lebih cepat daripada teknologi mengurangi kebutuhan terhadap tenaga kerja manusia?</p>',
    'sea-workers-ai-028':'Informal bukan berarti tidak relevan',
    'sea-workers-ai-029':'Yuval Noah Harari memperkenalkan salah satu gagasan paling provokatif dalam perdebatan AI, yaitu kemungkinan munculnya “kelas yang tidak lagi dibutuhkan”. Istilah ini sengaja terasa tidak nyaman. Harari tidak mengatakan bahwa manusia menjadi tidak berguna bagi keluarga, komunitas, atau masyarakat. Ia menggambarkan bahaya politik dan ekonomi ketika seseorang tetap bernilai sebagai manusia, tetapi pasar tidak lagi membutuhkan atau memberi imbalan yang layak atas tenaga kerja yang dapat ditawarkannya.',
    'sea-workers-ai-031':'Gagasan tersebut berguna sebagai kerangka berpikir, bukan sebagai perkiraan jumlah orang yang pasti akan tersingkir. Bukti yang tersedia saat ini lebih banyak mengukur pekerjaan dan tugas yang dapat diperkuat atau terganggu oleh AI. Bukti itu belum dapat memastikan berapa banyak orang yang akan menjadi pengangguran dalam jangka panjang, apalagi berapa banyak yang akan menjadi “tidak relevan”.',
    'sea-workers-ai-032':'Sejarah memberi alasan untuk optimistis sekaligus berhati-hati. Industrialisasi menggantikan banyak tugas yang sebelumnya dilakukan secara manual, tetapi tidak membuat manusia kehilangan relevansi ekonomi. Mesin mengambil alih sebagian pekerjaan fisik, lalu menciptakan permintaan baru untuk teknisi, operator, manajer, insinyur, tenaga penjualan, desainer, dan profesi yang sebelumnya belum ada. Tenaga kerja manusia tidak hilang, tetapi beralih ke bentuk pekerjaan yang baru.',
    'sea-workers-ai-033':'Namun, transisi itu tidak pernah tanpa rasa sakit dan manfaatnya juga tidak terbagi secara merata. Sejumlah pekerjaan hilang lebih cepat daripada pekerjaan baru tercipta. Sebagian komunitas dan industri membutuhkan waktu puluhan tahun untuk pulih. Revolusi AI dapat mengikuti pola serupa, tetapi kecepatannya berpotensi jauh lebih tinggi. Karena itu, relevansi ekonomi tidak datang dengan sendirinya. Relevansi perlu dibangun melalui pendidikan, produktivitas, dukungan institusi, dan kebijakan publik yang adil.',
    'sea-workers-ai-034':'Pendidikan adalah kunci untuk tetap relevan',
    'sea-workers-ai-035':'Asia Tenggara memiliki tenaga kerja yang muda dan terus bertumbuh. Namun, banyak orang memasuki pasar kerja tanpa menyelesaikan jenjang pendidikan yang penting.',
    'sea-workers-ai-038':'Sebelum membahas kompetensi teknis untuk menggunakan AI, masyarakat membutuhkan imajinasi untuk melihat apa yang dapat dicapai dengan teknologi. Petani mungkin ingin meningkatkan hasil panen sebesar 20% atau menurunkan biaya pupuk sebesar 10%. Pemilik usaha kecil mungkin ingin menjangkau pelanggan dua kali lebih banyak tanpa menggandakan biaya operasional. Mewujudkan gagasan tersebut membutuhkan kemampuan menghitung risiko, menguji asumsi, dan menilai apakah manfaat yang diharapkan sepadan dengan biayanya. AI dapat menghasilkan pilihan dan menganalisis skenario. Namun, AI tidak dapat menentukan sendiri tujuan mana yang layak diperjuangkan atau risiko apa yang dapat diterima oleh sebuah komunitas. Keputusan itu membutuhkan kebijaksanaan, rasa ingin tahu, dan keterbukaan terhadap temuan tak terduga.',
    'sea-workers-ai-042':'Dua kecenderungan ini mengarah pada pelajaran yang sama. Ketika pekerjaan teknis dan informasi menjadi semakin mudah diakses, keunggulan berpindah kepada orang yang mampu memahami tujuan, menyusun masalah dengan tepat, berkomunikasi secara jelas, mengambil keputusan, dan bertanggung jawab atas hasilnya.',
    'sea-workers-ai-043':'Bahasa Inggris dan bahasa internasional lainnya juga merupakan bagian dari kesiapan tersebut. Asia Tenggara memiliki tenaga kerja yang relatif terjangkau dan terus berkembang dalam bidang jasa digital. Developer, desainer, akuntan, analis, pemasar, dan konsultan dapat menggunakan AI untuk meningkatkan produktivitas serta bersaing mendapatkan klien internasional tanpa harus meninggalkan negaranya. Kemampuan berbahasa mengubah keterampilan lokal menjadi jasa yang dapat diekspor. Seseorang dapat tetap bekerja dari Indonesia, Filipina, Vietnam, atau Thailand sambil memperoleh akses ke pasar dengan daya beli dan tingkat pendapatan yang lebih tinggi.',
    'sea-workers-ai-044':'Pendidikan untuk era AI perlu menggabungkan dasar akademis, kompetensi teknis, kreativitas, komunikasi, pertimbangan yang matang, dan kemampuan belajar sepanjang hayat. Tujuannya bukan sekadar mencetak pengguna AI yang lebih cepat. Tujuannya adalah membentuk manusia yang mampu memilih masalah yang layak diselesaikan, mengajukan pertanyaan yang lebih baik, bekerja dengan orang lain, dan mengarahkan teknologi untuk menciptakan nilai nyata.',
    'sea-workers-ai-045':'Produktivitas adalah jalan menuju relevansi ekonomi',
    'sea-workers-ai-047':'Angka tersebut tidak berarti bahwa pekerja di satu negara bekerja lebih keras daripada pekerja di negara lain. Produktivitas per pekerja dipengaruhi oleh modal, teknologi, infrastruktur, pendidikan, struktur industri, dan kemampuan manajemen. Namun, perbedaan itu tetap memperlihatkan tantangan utama Asia Tenggara. Kawasan ini tidak kekurangan pekerja atau aktivitas ekonomi. Tantangannya adalah membantu lebih banyak pekerja menciptakan nilai yang lebih besar dari waktu, keterampilan, dan sumber daya yang mereka miliki.',
    'sea-workers-ai-048':'Peningkatan tersebut dapat dimulai melalui lima jalur yang mudah dipahami. Pekerja dapat menghasilkan lebih banyak dari sumber daya yang sama, menggunakan input yang lebih sedikit untuk output yang sama, meningkatkan kualitas hasil, memberikan pengalaman yang lebih baik, atau menjangkau pasar yang lebih luas. Teknologi digital dan AI dapat mendukung kelima jalur tersebut tanpa harus menghapus peran manusia.',
    'sea-workers-ai-049':'1. Menghasilkan lebih banyak',
    'sea-workers-ai-050':'Menghasilkan lebih banyak berarti meningkatkan output dari jumlah lahan, waktu, tenaga kerja, modal, dan peralatan yang sama. Ukurannya harus nyata, seperti jumlah produk per hari, hasil panen per hektare, atau pendapatan per jam kerja. Bagi petani, teknologi dapat menggabungkan prakiraan cuaca, pemantauan tanaman, rekomendasi pupuk, pencatatan, dan akses pasar. Seorang petani yang meningkatkan hasil dari empat ton menjadi enam ton per hektare telah meningkatkan produktivitas sebesar 50% tanpa memperluas lahan.',
    'sea-workers-ai-051':'2. Menggunakan lebih sedikit input',
    'sea-workers-ai-052':'Menggunakan lebih sedikit input berarti mempertahankan output sambil mengurangi bahan baku, energi, waktu, limbah, atau biaya. Ukurannya dapat berupa konsumsi energi per unit, tingkat cacat, jam henti mesin, atau biaya produksi. Sebuah pabrik kecil dapat menggunakan sensor digital dan pemeliharaan prediktif untuk mendeteksi masalah lebih awal, mengurangi kerusakan, dan menjaga produksi dengan listrik serta waktu henti yang lebih rendah. Nilainya bukan berasal dari mempekerjakan lebih sedikit orang, tetapi dari membantu pekerja dan mesin menggunakan sumber daya secara lebih efisien.',
    'sea-workers-ai-053':'3. Meningkatkan kualitas',
    'sea-workers-ai-054':'Meningkatkan kualitas berarti menghasilkan produk yang lebih konsisten, andal, menarik, atau bernilai tanpa menambah sumber daya secara sebanding. Ukurannya dapat berupa tingkat pengembalian barang, ulasan pelanggan, jumlah keluhan, pembelian berulang, atau harga jual rata-rata. Penjual e-commerce dapat menggunakan pencatatan digital, analisis umpan balik, dan AI untuk memperbaiki deskripsi produk, kemasan, kontrol kualitas, serta layanan pelanggan. Jumlah barang yang terjual mungkin tetap sama, tetapi penjual dapat memperoleh penilaian lebih baik, lebih sedikit pengembalian, dan pendapatan yang lebih tinggi per produk.',
    'sea-workers-ai-055':'4. Melayani dengan lebih baik',
    'sea-workers-ai-056':'Melayani dengan lebih baik berarti menciptakan pengalaman yang lebih cepat, mudah, personal, atau berkesan menggunakan kapasitas yang sama. Ukurannya dapat berupa waktu tunggu, tingkat penyelesaian pemesanan, kepuasan pelanggan, kunjungan berulang, atau pengeluaran wisatawan. Dalam sektor pariwisata Asia Tenggara, teknologi dapat menyederhanakan pencarian, pemesanan, pembayaran, penerjemahan, dan perencanaan perjalanan. Namun, pengalaman terbaik tetap bergantung pada manusia. Pemandu wisata, pengemudi, pemilik penginapan, dan pedagang lokal memberikan pengetahuan, keramahan, dan rasa percaya yang tidak dapat digantikan oleh sistem pemesanan.',
    'sea-workers-ai-057':'5. Menjangkau pasar yang lebih luas',
    'sea-workers-ai-058':'Menjangkau pasar yang lebih luas berarti menggunakan keterampilan dan kapasitas yang sama untuk melayani lebih banyak pelanggan, termasuk pelanggan di luar kota atau negara asal. Ukurannya dapat berupa jumlah pasar yang dilayani, pelanggan internasional, pendapatan ekspor, pendapatan per pekerja, atau tarif rata-rata proyek. Developer di Filipina, desainer di Indonesia, editor video di Vietnam, dan akuntan di Malaysia dapat menggunakan platform digital, AI, pembayaran daring, dan bahasa Inggris untuk bekerja bagi klien global dari negara mereka sendiri. Mereka tidak harus bermigrasi untuk memperoleh akses ke pasar dengan pendapatan yang lebih tinggi.',
    'sea-workers-ai-060':'Bagi pekerja Asia Tenggara, terutama mereka yang berada di ekonomi informal, AI dan teknologi tidak harus membuat peran mereka usang. Namun, keduanya akan mengubah cara nilai ekonomi diciptakan dan dihargai. Dengan memanfaatkan teknologi digital dan AI, pekerja dapat tetap relevan dengan meningkatkan produktivitas serta kemampuan mereka. Teknologi dapat membantu menghasilkan lebih banyak, mengurangi biaya dan limbah, memperbaiki kualitas, meningkatkan pengalaman pelanggan, dan menjangkau pasar yang lebih luas. Dalam kerangka ini, AI bukan alat untuk menghapus pekerja sepenuhnya. AI menjadi alat yang memperbesar kemampuan manusia dan membantu pekerja menciptakan nilai yang lebih besar dari keterampilan, waktu, serta sumber daya yang mereka miliki.',
    'sea-workers-ai-061':'Pekerja tidak dapat beradaptasi sendirian',
    'sea-workers-ai-063':'Karena jutaan orang bergantung pada institusi tersebut untuk memperoleh pendapatan dan akses pasar, keputusan yang mereka ambil membutuhkan kebijaksanaan dan rasa adil. Skala seharusnya tidak dipandang semata-mata sebagai peluang untuk mengambil nilai lebih besar dari pekerja dan pedagang. Skala juga membawa tanggung jawab untuk memperkuat kemakmuran, keselamatan, daya tawar, dan ketahanan jangka panjang para mitra yang menopang ekosistem.',
    'sea-workers-ai-064':'1. Platform dapat membuka akses pasar',
    'sea-workers-ai-066':'Angka yang dilaporkan perusahaan tidak menunjukkan berapa banyak orang yang menjadikan platform sebagai sumber pendapatan utama. Namun, angka itu memperlihatkan besarnya peluang. Keterampilan produktif memiliki nilai terbatas tanpa akses terhadap permintaan. Platform dapat menghubungkan pekerja mandiri dan usaha kecil dengan pelanggan yang sebelumnya sulit atau mahal untuk dijangkau. Karena itu, platform seharusnya tidak melihat skala hanya sebagai peluang untuk menarik komisi, biaya, dan data sebanyak mungkin. Pertumbuhan mereka juga harus memperkuat kemakmuran, keselamatan, daya tawar, serta ketahanan para mitra yang menciptakan nilai di dalam ekosistem.',
    'sea-workers-ai-067':'2. Data dapat membuka akses pembiayaan dan perlindungan',
    'sea-workers-ai-070':'Teknologi dapat membantu memperluas akses pembiayaan, tetapi harus digunakan untuk membangun kemampuan dan ketahanan. Tujuannya bukan membuat pekerja informal bergantung pada utang berlebihan atau produk keuangan yang tidak mereka pahami. Data seharusnya membantu institusi mengenali pekerja yang produktif, menawarkan persyaratan yang wajar, memperluas perlindungan, dan mendukung pertumbuhan jangka panjang.',
    'sea-workers-ai-071':'3. Kemitraan dapat berbagi kemampuan',
    'sea-workers-ai-072':'Perusahaan besar dapat membantu pekerja dan usaha informal memperoleh kemampuan yang sulit mereka bangun sendiri. Perusahaan dapat menjadi pembeli yang stabil, menghubungkan produk lokal dengan pasar nasional atau ekspor, berbagi standar mutu, menyediakan pelatihan, serta membuka akses terhadap logistik, teknologi, pengemasan, dan distribusi. Koperasi dan organisasi sektoral juga dapat menghimpun produsen kecil agar mereka dapat memenuhi pesanan lebih besar dan bernegosiasi dari posisi yang lebih kuat.',
    'sea-workers-ai-073':'Bentuk kemitraan ini penting karena produktivitas saja belum tentu menghasilkan pendapatan yang lebih tinggi. Petani dapat meningkatkan hasil panen, tetapi tetap tertekan jika tidak memiliki pembeli yang andal atau informasi harga. Pengrajin dapat membuat produk yang lebih baik, tetapi tetap terkurung di pasar lokal. Perusahaan seharusnya tidak memandang pemasok dan pekerja kecil hanya sebagai sumber biaya murah. Kemitraan yang sehat perlu berbagi pengetahuan, akses pasar, risiko, dan manfaat agar kedua pihak dapat bertumbuh.',
    'sea-workers-ai-074':'Ketiga jalur ini menunjukkan peran penting ekonomi formal. Namun, jalur yang sama juga dapat menciptakan ketergantungan baru ketika satu institusi menguasai visibilitas pelanggan, data transaksi, pembiayaan, harga, dan akses terhadap pekerjaan. Tujuan akhirnya adalah memastikan semua orang tetap relevan secara ekonomi dan memperoleh peluang yang lebih setara. Transformasi digital tidak boleh menjadi sistem baru untuk mengekstraksi nilai sebesar-besarnya demi keuntungan segelintir perusahaan, investor, atau institusi.',
    'sea-workers-ai-075':'Pemerintah harus menjaga keadilan ekonomi digital',
    'sea-workers-ai-077':'Pemerintah berperan sebagai penengah ketika kekuatan tawar antara pekerja dan platform sangat tidak seimbang. Regulasi yang baik harus melindungi pendapatan, keselamatan, data, kebebasan memilih, dan akses pekerja terhadap mekanisme yang bermakna untuk menggugat keputusan. Pada saat yang sama, aturan perlu cukup jelas dan dapat diprediksi agar perusahaan tetap dapat berinovasi, berinvestasi, dan bersaing.',
    'sea-workers-ai-078':'1. Memperluas perlindungan sosial di luar pekerjaan formal',
    'sea-workers-ai-080':'Perlindungan sosial tidak seharusnya bergantung pada ada atau tidaknya hubungan kerja formal. Pemerintah dapat menggunakan sistem digital untuk menyederhanakan pendaftaran dan pembayaran, sekaligus meminta platform membantu penyampaian informasi serta integrasi perlindungan. Namun, kontribusi harus terjangkau dan manfaatnya mudah dipahami. Sistem yang hanya tersedia di atas kertas tidak akan melindungi pekerja.',
    'sea-workers-ai-082':'Malaysia menunjukkan bahwa pemerintah tidak harus memilih antara inovasi dan perlindungan. Bisnis platform tetap dapat bertumbuh, tetapi pekerja memerlukan hak yang jelas, proses yang adil, dan ruang untuk menyuarakan keberatan terhadap keputusan yang memengaruhi penghidupan mereka. Prinsip serupa dapat diterapkan pada ekonomi digital yang lebih luas, mulai dari layanan transportasi hingga pasar e-commerce.',
    'sea-workers-ai-083':'3. Membatasi ekstraksi nilai yang tersembunyi',
    'sea-workers-ai-084':'Ekonomi digital dapat mengurangi sebagian biaya transaksi sekaligus menciptakan biaya baru yang sulit dilihat. Pengemudi mungkin mengetahui tarif komisi yang terlihat di permukaan, tetapi tidak memahami bagaimana bonus, prioritas pesanan, atau penalti dihitung. Penjual e-commerce dapat bergabung ke marketplace tanpa biaya besar, tetapi kemudian menemukan bahwa produknya hampir tidak terlihat kecuali membayar iklan, mengikuti program promosi, atau memberikan diskon.',
    'sea-workers-ai-085':'Masalahnya bukan semata-mata bahwa platform mengenakan biaya. Platform menyediakan teknologi, pemasaran, pembayaran, kepercayaan, dan logistik yang nyata. Masalah muncul ketika pekerja dan penjual tidak dapat memahami total biaya akses, membandingkan pilihan secara wajar, atau menolak syarat tertentu tanpa kehilangan penghasilan. Pemerintah dapat mewajibkan pengungkapan biaya yang lebih jelas, persetujuan aktif atas layanan berbayar, aturan yang transparan mengenai visibilitas, dan pemberitahuan sebelum perubahan besar diterapkan.',
    'sea-workers-ai-086':'4. Memberikan hak untuk memahami dan menggugat keputusan otomatis',
    'sea-workers-ai-088':'Setidaknya, pekerja dan penjual berhak mengetahui kapan keputusan otomatis digunakan, kategori data apa yang memengaruhinya, serta cara meminta peninjauan oleh manusia. Jika sebuah sistem dapat menurunkan penghasilan seseorang, orang tersebut perlu memiliki cara yang realistis untuk memperbaiki kesalahan. Transparansi tidak mengharuskan perusahaan membuka seluruh algoritmanya. Transparansi berarti memberikan penjelasan yang cukup agar pihak terdampak dapat memahami hasil dan menggunakan haknya.',
    'sea-workers-ai-089':'5. Menjaga kebebasan memilih dan persaingan',
    'sea-workers-ai-090':'Ketika satu platform menjadi pintu utama menuju pelanggan, pekerja dan penjual dapat kehilangan kebebasan memilih. Pemerintah harus mengawasi klausul eksklusivitas, hukuman karena menggunakan beberapa platform, perpindahan data yang tidak adil, dan praktik yang mengunci pengguna dalam satu ekosistem. Persaingan penting bagi pekerja informal karena alternatif memberi mereka daya tawar. Jika pelanggan, reputasi, dan riwayat transaksi sepenuhnya terkurung dalam satu platform, kebebasan untuk keluar hanya ada secara teori.',
    'sea-workers-ai-091':'AI dan teknologi tidak harus menjadi pengganti manusia. Di Asia Tenggara, keduanya dapat menjadi sarana untuk memperbesar kemampuan manusia. Teknologi dapat membantu petani memperoleh hasil lebih tinggi, pedagang menjangkau pelanggan baru, pengemudi bekerja lebih aman, usaha kecil mengakses pembiayaan, dan tenaga profesional mengekspor jasanya tanpa meninggalkan negara asal. Namun, relevansi tersebut hanya dapat bertahan jika pendidikan membangun kemampuan beradaptasi, institusi berbagi manfaat produktivitas, dan pemerintah melindungi keadilan dalam ekonomi digital.',
    'sea-workers-ai-092':'Sejarah menunjukkan bahwa teknologi mengubah nilai ekonomi manusia, bukan menghapusnya. Pertanyaan pentingnya adalah siapa yang diberi kesempatan untuk beradaptasi, siapa yang menguasai alat produktif, dan siapa yang menikmati manfaatnya. Asia Tenggara dapat memasuki era AI dengan memperlakukan manusia hanya sebagai biaya yang harus ditekan, atau dengan menggunakan teknologi agar lebih banyak orang mampu menciptakan nilai, memperoleh pendapatan, dan menjaga martabatnya. Tujuannya bukan mempertahankan setiap tugas tanpa perubahan. Tujuannya adalah memastikan bahwa ketika pekerjaan berubah, masyarakat tetap memiliki jalan untuk tetap relevan.',
    'sea-workers-ai-094':'← Kembali ke semua catatan',
    'sea-workers-ai-095':'Bagikan artikel',
    'sea-workers-ai-096':'Salin tautan',
    'sea-workers-ai-097':'Portofolio',
    'sea-workers-ai-099':'Kontak'
  });

  [
    ['sea-workers-ai','sea-workers-ai-022','Pada 2024, 69,3% tenaga kerja ASEAN bekerja secara informal, setara dengan sekitar tujuh dari setiap sepuluh pekerja. Indonesia menunjukkan besarnya skala tersebut. Pada Februari 2026, 87,74 juta dari 147,67 juta penduduk bekerja di Indonesia berada di sektor informal, atau sekitar 59% dari total tenaga kerja.'],
    ['sea-workers-ai','sea-workers-ai-030','Pada 2017, Harari memperkirakan bahwa menjelang 2050 dapat muncul sebuah kelas baru yang anggotanya bukan hanya menganggur, tetapi juga semakin sulit dipekerjakan. Di Davos pada 2020, ia menjelaskan bahwa kata “tidak berguna” merujuk pada ketidakbergunaan bagi sistem ekonomi dan politik, bukan bagi keluarga dan teman. Ia juga menegaskan bahwa hasil tersebut adalah sebuah kemungkinan, bukan ramalan.'],
    ['sea-workers-ai','sea-workers-ai-036','Menurut ASEAN Employment Outlook, hampir separuh pemuda usia akhir di kawasan belum menyelesaikan pendidikan menengah pertama dan hampir tiga dari empat belum lulus pendidikan tinggi. Kesenjangan tersebut menjadi tantangan serius ketika AI mulai mengubah pekerjaan serta keterampilan yang dibutuhkan. Jutaan pekerja akan diminta mempelajari alat baru dan beralih ke tugas baru, sering kali tanpa pendidikan dasar, pelatihan teknis, atau akses pembelajaran berkelanjutan yang memadai.'],
    ['sea-workers-ai','sea-workers-ai-046','Pendidikan dapat membantu pekerja tetap adaptif. Namun, relevansi ekonomi pada akhirnya bergantung pada kemampuan pengetahuan dan keterampilan untuk menghasilkan output yang lebih tinggi, kualitas yang lebih baik, biaya yang lebih rendah, atau pendapatan yang lebih besar. Produktivitas masih menjadi tantangan utama di Asia Tenggara. Singapura merupakan pengecualian yang jelas dengan output per pekerja sekitar US$115.334 pada 2025. Di antara ekonomi besar kawasan, Malaysia berada jauh di bawahnya dengan US$24.566 per pekerja, disusul Thailand sekitar US$12.073, Indonesia US$9.278, dan Vietnam US$7.475. Sejumlah negara ASEAN lain berada di bawah tingkat tersebut.'],
    ['sea-workers-ai','sea-workers-ai-065','Besarnya jangkauan platform menunjukkan dampaknya. Sea melaporkan sekitar 26,5 juta penjual aktif di Shopee pada 2025. Dalam laporan keberlanjutannya, GoTo menyebut lebih dari 3,1 juta mitra pengemudi dan sekitar 20,1 juta merchant di dalam ekosistemnya. Grab juga melaporkan lebih dari 5 juta mitra pengemudi dan lebih dari 13 juta mitra merchant di Asia Tenggara pada akhir 2025.'],
    ['sea-workers-ai','sea-workers-ai-069','Lembaga formal dapat menggunakan jejak digital untuk menilai kemampuan membayar dengan cara yang lebih sesuai bagi pekerja informal. Riwayat penjualan, hasil panen, pembayaran, atau pekerjaan di platform dapat membantu membangun profil risiko bagi seseorang yang sebelumnya dianggap tidak layak menerima kredit menurut kriteria perbankan. Perusahaan teknologi pertanian seperti Crowde dan Amartha telah menunjukkan bagaimana data dan jaringan lapangan dapat menghubungkan petani serta usaha mikro dengan pendanaan yang sebelumnya sulit mereka akses.'],
    ['sea-workers-ai','sea-workers-ai-079','Indonesia menyediakan program BPJS Ketenagakerjaan untuk Bukan Penerima Upah, yang mencakup pekerja mandiri dan pekerja informal. Peserta dapat memperoleh perlindungan kecelakaan kerja, kematian, hari tua, dan kehilangan penghasilan melalui iuran yang disesuaikan dengan kategori pekerja.'],
    ['sea-workers-ai','sea-workers-ai-081','Malaysia memberikan contoh regional yang lebih luas. Gig Workers Act mulai berlaku pada Maret 2026 dan diperkirakan melindungi sekitar 1,64 juta pekerja gig. Undang-undang tersebut mengatur potongan yang tidak adil, keputusan otomatis, perlindungan sosial, mekanisme pengaduan, dan akses ke tribunal khusus.'],
    ['sea-workers-ai','sea-workers-ai-087','Platform dapat menonaktifkan akun karena dugaan penipuan, membatalkan pesanan, menurunkan peringkat penjual, atau mengurangi visibilitas berdasarkan sistem otomatis. Keputusan tersebut dapat dibenarkan untuk menjaga kepercayaan dan keselamatan. Namun, kesalahan juga dapat terjadi. Pengemudi dapat kehilangan akses karena laporan yang keliru. Penjual dapat dihukum karena transaksi yang tidak mereka kendalikan. Jika hasil penyelidikan menyatakan pekerja tidak bersalah, pemulihan akses dan penghasilan harus dilakukan dengan cepat.']
  ].forEach(([page,key,value])=>replaceText(page,key,value));

  assign('field-evidence',{
    'field-evidence-006':'Foto',
    'field-evidence-008':'← Semua catatan',
    'field-evidence-009':'Membangun Venture Iklim',
    'field-evidence-010':'Dari Bukti Lapangan Menuju Uji Coba yang Terukur',
    'field-evidence-011':'Pelajaran dari mendampingi tim NomaTech Challenge untuk COP17 dalam mengubah gagasan iklim menjadi uji coba yang kredibel, model bisnis yang kuat, dan narasi venture berbasis bukti.',
    'field-evidence-014':'10 menit membaca',
    'field-evidence-016':'Membangun venture',
    'field-evidence-019':'Uji coba iklim yang kredibel menghubungkan bukti lapangan dengan asumsi yang jelas, lalu menguji apakah gagasan tersebut dapat bekerja bagi masyarakat di tempat tertentu.',
    'field-evidence-020':'Saya bergabung dengan NomaTech Challenge untuk COP17 sebagai pembicara dan mentor global dengan satu tugas praktis. Saya membantu tim tahap awal bergerak dari gagasan iklim yang menarik menuju uji coba yang benar-benar dapat dijalankan, didanai, dan dijadikan sumber pembelajaran.',
    'field-evidence-021':'Sesi ini dirancang berdasarkan masalah yang sering saya temui dalam venture building. Tim dapat menjelaskan teknologi yang ingin mereka ciptakan, tetapi masih kesulitan menjawab masalah siapa yang diselesaikan, bagaimana solusi akan diterapkan, perubahan lokal apa yang ingin dihasilkan, dan apakah model ekonominya dapat berjalan. Masalahnya jarang terletak pada kurangnya semangat. Yang sering hilang adalah hubungan yang jelas di antara setiap bagian.',
    'field-evidence-024':'Gagasan iklim belum tentu menjadi uji coba',
    'field-evidence-025':'Uji coba yang kuat harus memenuhi tiga syarat sekaligus.',
    'field-evidence-026':'Uji coba harus dibutuhkan. Pengguna nyata perlu cukup peduli terhadap masalahnya sehingga bersedia mengubah perilaku, meluangkan waktu, atau membayar. Uji coba juga harus dapat diwujudkan. Tim perlu mampu menghadirkan solusi dengan teknologi, mitra, dan kondisi operasional yang tersedia. Terakhir, uji coba harus layak secara ekonomi. Logika pendapatan, struktur biaya, dan jalur pendanaan perlu menopang sesuatu yang lebih bertahan lama daripada eksperimen satu kali.',
    'field-evidence-027':'Uji coba menjadi kredibel ketika kebutuhan pengguna, kelayakan teknis, dan kelayakan ekonomi saling memperkuat.',
    'field-evidence-028':'Tim sering memperlakukan ketiganya sebagai alur kerja yang terpisah. Wawancara pelanggan berada di satu dokumen, rancangan teknis di dokumen lain, dan model keuangan di tempat berbeda. Pendekatan yang lebih baik adalah menghubungkannya. Keputusan desain perlu merespons bukti tentang pengguna. Cara penyampaian solusi harus terlihat dalam model biaya. Klaim dampak perlu dikaitkan dengan perilaku atau kondisi yang dapat diamati selama uji coba.',
    'field-evidence-029':'Itulah sebabnya uji coba dengan ruang lingkup sempit dapat lebih berharga daripada konsep yang terlalu luas. Pendekatan ini memaksa tim menentukan siapa melakukan apa, di mana pengujian berlangsung, sumber daya apa yang diperlukan, dan hasil apa yang dapat membenarkan langkah berikutnya.',
    'field-evidence-030':'Perlakukan kanvas sebagai sembilan hipotesis',
    'field-evidence-032':'Pada tahap awal, kanvas bukan gambaran bisnis yang telah terbukti. Kanvas adalah peta asumsi.',
    'field-evidence-033':'Kanvas Model Bisnis menjadi lebih berguna ketika setiap blok diperlakukan sebagai hipotesis yang masih membutuhkan bukti.',
    'field-evidence-034':'Segmen pelanggan merupakan hipotesis tentang siapa yang mengalami masalah. Proposisi nilai adalah hipotesis tentang sesuatu yang cukup penting untuk mengubah perilaku. Saluran merupakan hipotesis tentang cara tim menjangkau dan mendukung pengguna. Pendapatan dan biaya merupakan hipotesis tentang apakah nilai dapat ditangkap tanpa merusak kemampuan tim untuk menghadirkan solusi.',
    'field-evidence-036':'Perbedaan lain juga penting bagi venture iklim dan pembangunan. Pengguna, penerima manfaat, dan pembayar tidak selalu merupakan orang yang sama. Petani dapat menggunakan sebuah solusi, rumah tangga menerima manfaatnya, dan lembaga lokal membayarnya. Jika tim menggabungkan ketiga peran tersebut ke dalam satu kategori “pelanggan” yang tidak jelas, logika produk, saluran, dan harga akan menjadi rancu.',
    'field-evidence-037':'Pisahkan bukti dari asumsi',
    'field-evidence-038':'Disiplin paling berguna dalam lokakarya ini sebenarnya sederhana. Pisahkan apa yang telah diamati tim dari apa yang masih mereka yakini.',
    'field-evidence-039':'Bukti perlu mengarah pada asumsi yang jelas, kemudian pada pengujian yang dapat mengubah keputusan tim.',
    'field-evidence-040':'Bukti dapat berasal dari wawancara, observasi, catatan lapangan, penerapan sebelumnya, atau data publik yang kredibel. Asumsi adalah penafsiran terhadap bukti tersebut. Pengujian adalah tindakan berikutnya yang dirancang untuk mengonfirmasi, menolak, atau menyempurnakan asumsi.',
    'field-evidence-041':'Sebagai contoh, keterangan bahwa rumah tangga menghadapi kualitas air yang tidak stabil merupakan bukti adanya masalah. Keyakinan bahwa mereka bersedia membayar biaya bulanan untuk pemantauan merupakan asumsi. Menawarkan uji coba berbayar dalam skala terbatas kepada kelompok yang jelas merupakan sebuah pengujian.',
    'field-evidence-042':'Memisahkan ketiga kategori ini mencegah rasa percaya diri tumbuh lebih cepat daripada pengetahuan. Langkah ini juga membuat masukan mentor lebih berguna karena diskusi dapat berfokus pada mata rantai terlemah, bukan memperdebatkan seluruh gagasan sekaligus.',
    'field-evidence-043':'Jangan menyamakan keluaran dengan dampak',
    'field-evidence-047':'Keluaran prototipe mendorong perubahan perilaku. Perubahan perilaku menghasilkan dampak lokal. Dampak lokal kemudian berkontribusi pada perubahan yang lebih luas.',
    'field-evidence-049':'Untuk venture air, indikatornya dapat berupa berkurangnya jumlah hari dengan hasil pengukuran yang tidak aman, menurunnya waktu henti pengolahan, atau meningkatnya penerapan praktik yang lebih aman. Untuk venture restorasi lahan, indikatornya dapat berupa tingkat kelangsungan hidup tanaman, kondisi tanah, atau perubahan cara lahan dikelola. Indikator tidak perlu membuktikan dampak global selama uji coba. Indikator hanya perlu menunjukkan apakah jalur perubahan yang dirancang benar-benar bekerja.',
    'field-evidence-050':'Ubah kanvas menjadi angka',
    'field-evidence-051':'Model bisnis yang kredibel pada akhirnya harus bergerak dari kanvas menuju model keuangan.',
    'field-evidence-053':'Segmen pelanggan memengaruhi jumlah calon pembeli. Saluran memengaruhi biaya akuisisi dan dukungan pelanggan. Aktivitas utama menentukan kebutuhan tenaga kerja serta biaya operasional. Mitra dapat mengurangi kebutuhan modal, tetapi juga dapat mengambil margin atau menciptakan ketergantungan. Harga baru menghasilkan pendapatan ketika dikaitkan dengan perkiraan adopsi, frekuensi penggunaan, dan retensi.',
    'field-evidence-054':'Dalam sesi tersebut, saya menggunakan SteppeWater sebagai studi kasus gabungan untuk pembelajaran, bukan sebagai perusahaan nyata. Tujuannya adalah membuat kerangka ini lebih konkret. Contoh tersebut menunjukkan cara menerjemahkan solusi ke dalam anggaran uji coba berskala kecil, lalu memisahkan biaya tetap, biaya variabel, dan biaya bertahap sebelum mengajukan klaim pertumbuhan yang lebih besar.',
    'field-evidence-055':'Tujuannya bukan menghasilkan proyeksi yang sempurna. Angka pada tahap awal pasti berubah. Tujuannya adalah membuat setiap asumsi cukup jelas untuk diuji.',
    'field-evidence-056':'Model uji coba yang berguna perlu menjawab beberapa pertanyaan dasar. Berapa banyak pengguna yang dilibatkan? Siapa yang membayar? Berapa biaya setiap penerapan? Biaya apa yang terus berulang? Apa yang berubah ketika uji coba diperluas ke lokasi lain? Bukti apa yang dapat mendukung harga lebih tinggi atau biaya penerapan lebih rendah?',
    'field-evidence-057':'Ketika pertanyaan tersebut dinyatakan dengan jelas, model menjadi alat pembelajaran, bukan sekadar hiasan untuk penggalangan dana.',
    'field-evidence-058':'Bangun narasi venture yang utuh',
    'field-evidence-059':'Tim sering memiliki seluruh komponen yang tepat, tetapi menyajikannya sebagai fakta yang berdiri sendiri. Narasi venture yang kuat membentuk alur logis dari masalah hingga kebutuhan pendanaan.',
    'field-evidence-060':'Pitch yang kuat adalah rangkaian bukti dan keputusan, bukan kumpulan slide yang terlihat mengesankan.',
    'field-evidence-061':'Masalah perlu menjelaskan mengapa tindakan dibutuhkan. Bukti menunjukkan bahwa masalah tersebut nyata dan spesifik. Solusi merespons bukti itu. Uji coba menjelaskan hal yang akan diuji tim. Jalur dampak menunjukkan perubahan yang diharapkan. Model bisnis menjelaskan cara penerapan dapat terus berlangsung. Terakhir, kebutuhan pendanaan harus membiayai tahap pembuktian berikutnya.',
    'field-evidence-062':'Ketika seluruh elemen tersebut terhubung, pitch menjadi lebih mudah dipercaya. Audiens tidak lagi harus mengisi sendiri bagian yang hilang dari cerita tim.',
    'field-evidence-063':'Hubungan yang jelas juga memperbaiki kualitas permintaan pendanaan. Alih-alih meminta modal untuk sekadar “bertumbuh”, tim dapat meminta jumlah tertentu untuk menjalankan pengujian yang jelas, mencapai tonggak yang terukur, dan mengurangi risiko yang telah ditentukan.',
    'field-evidence-064':'Gunakan AI sebagai rekan kerja, bukan sumber kebenaran',
    'field-evidence-065':'Bagian praktik dalam sesi ini menggunakan AI untuk membantu tim menganalisis bukti, menguji asumsi, dan menyusun bagian dari model. Prinsipnya sederhana. AI membantu tim berpikir, tetapi tim tetap menentukan apa yang dapat dipercaya.',
    'field-evidence-066':'Lokakarya memberikan porsi waktu terbesar untuk analisis, tetapi tetap menyisakan waktu khusus untuk peninjauan dan pengambilan keputusan oleh manusia.',
    'field-evidence-067':'AI dapat dengan cepat menyusun catatan wawancara, menemukan kontradiksi, menghasilkan alternatif model pendapatan, atau mengusulkan risiko yang terlewat. Namun, AI juga dapat menghasilkan jawaban yang terdengar meyakinkan dari masukan yang lemah. Karena itu, validasi tetap penting.',
    'field-evidence-068':'Alur kerja yang paling produktif bukanlah “meminta AI membuat model bisnis”. Tim perlu memberikan bukti yang spesifik, lalu meminta AI mengidentifikasi asumsi, membandingkan alternatif, dan memperjelas ketidakpastian. Setelah itu, tim memeriksa hasilnya berdasarkan pengetahuan lokal, percakapan dengan pemangku kepentingan, dan kenyataan operasional.',
    'field-evidence-069':'Bagi venture iklim, perbedaan ini sangat penting. Konteks berbeda di setiap komunitas, bentang alam, dan institusi. Jawaban umum yang terdengar masuk akal tetap dapat keliru untuk suatu tempat tertentu.',
    'field-evidence-070':'Pelajaran yang saya bawa sebagai mentor',
    'field-evidence-071':'Sesi ini memperkuat keyakinan yang selalu saya bawa dalam pekerjaan investasi dan pendampingan startup. Venture tahap awal tidak menjadi kredibel dengan menghilangkan seluruh ketidakpastian. Kredibilitas tumbuh ketika tim mampu menyebutkan ketidakpastian yang paling penting dan merancang cara belajar yang disiplin.',
    'field-evidence-072':'Tim terkuat belum tentu memiliki visual paling rinci atau model keuangan paling panjang. Tim terkuat mampu menjelaskan apa yang telah diketahui, apa yang belum diketahui, dan pelajaran apa yang ingin diperoleh dari uji coba berikutnya.',
    'field-evidence-074':'Pesan penutup saya kepada peserta sederhana. Bangun alur cerita terlebih dahulu. Uji asumsi yang menyatukan cerita tersebut. Sempurnakan uji coba berdasarkan bukti yang ditemukan. Perluas hanya setelah langkah berikutnya terbukti berhasil.',
    'field-evidence-075':'Disiplin tersebut tidak hanya memperbaiki pitch. Disiplin itu memberi gagasan iklim yang menjanjikan peluang lebih besar untuk menjadi venture yang benar-benar bekerja di lapangan.',
    'field-evidence-077':'← Kembali ke semua catatan',
    'field-evidence-078':'Bagikan artikel',
    'field-evidence-079':'Salin tautan',
    'field-evidence-080':'Portofolio',
    'field-evidence-082':'Kontak'
  });

  [
    ['field-evidence','field-evidence-022','NomaTech dikembangkan dalam konteks UNCCD COP17 di Ulaanbaatar, Mongolia. Konferensi resmi berlangsung pada 17 hingga 28 Agustus 2026 dengan tema “Restoring Land. Restoring Hope.” Konteks tersebut membuat tantangan dalam sesi mentoring menjadi sangat relevan. Solusi lahan, air, dan iklim tidak dapat dinilai hanya dari prototipe yang terlihat sempurna. Solusi tersebut harus bekerja bagi masyarakat di tempat tertentu dan terus memberikan manfaat setelah demonstrasi awal berakhir.'],
    ['field-evidence','field-evidence-031','Kanvas Model Bisnis umumnya terdiri atas sembilan bagian. Sebuah kanvas dapat terlihat lengkap setelah setiap kotaknya terisi, tetapi kesan tersebut bisa menyesatkan.'],
    ['field-evidence','field-evidence-048','Pendekatan ini juga lebih tepat untuk menghubungkan venture dengan Tujuan Pembangunan Berkelanjutan. Kerangka Perserikatan Bangsa-Bangsa mencakup 17 tujuan. Tim sebaiknya tidak memulai dengan memilih lambang SDG yang paling menarik. Mulailah dengan menentukan perubahan lokal dan indikator yang dapat diamati secara kredibel. SDG yang relevan kemudian mengikuti logika perubahan tersebut.'],
    ['field-evidence','field-evidence-073','NomaTech Challenge untuk COP17 memperkenalkan saya sebagai mentor global yang membantu tim menyempurnakan pitch dan menyampaikannya secara profesional.']
  ].forEach(([page,key,value])=>replaceText(page,key,value));

  assign('sea-ai-boom',{
    'sea-ai-boom-006':'Foto',
    'sea-ai-boom-008':'← Semua catatan',
    'sea-ai-boom-009':'AI & Asia Tenggara',
    'sea-ai-boom-010':'Di Mana Asia Tenggara Dapat Unggul dalam Gelombang AI?',
    'sea-ai-boom-011':'Modal global semakin terkonsentrasi pada kecerdasan buatan. Namun, Asia Tenggara tidak harus bersaing langsung dalam pengembangan model AI terdepan. Peluang terbesarnya mungkin terletak pada penerapan AI untuk alur kerja lokal, serta pembangunan infrastruktur, perangkat keras, dan distribusi yang membuat teknologi ini berguna dalam skala besar.',
    'sea-ai-boom-014':'13 menit membaca',
    'sea-ai-boom-019':'Asia Tenggara tidak harus bersaing hanya pada lapisan model AI terdepan. Peluang kawasan ini terbentang dari alur kerja dan distribusi lokal hingga chip, pusat data, dan AI yang beroperasi di dunia fisik.',
    'sea-ai-boom-020':'Gelombang AI dan musim dingin pendanaan terjadi bersamaan',
    'sea-ai-boom-021':'Kecerdasan buatan telah menciptakan salah satu siklus investasi paling terkonsentrasi dalam beberapa tahun terakhir. Namun bagi Asia Tenggara, pertanyaan utamanya bukan apakah kawasan ini dapat melahirkan OpenAI berikutnya. Pertanyaan yang lebih penting adalah di bagian mana dari rantai nilai AI perusahaan Asia Tenggara dapat membangun keunggulan yang tahan lama.',
    'sea-ai-boom-024':'Kedua realitas itu tidak bertentangan. Keduanya menggambarkan pasar yang sama. Lebih banyak modal tersedia bagi perusahaan teknologi, tetapi investor semakin selektif dalam menentukan ke mana modal tersebut disalurkan.',
    'sea-ai-boom-025':'Perbedaan itu penting bagi founder. Label AI dapat membantu perusahaan memasuki percakapan, tetapi tidak menghapus kebutuhan untuk membuktikan permintaan, retensi, unit economics, tata kelola, dan jalur pertumbuhan yang kredibel. Di pasar yang selektif, “kami menggunakan AI” bukanlah tesis investasi. <strong>Hasil bisnis adalah tesis investasinya.</strong>',
    'sea-ai-boom-026':'Gambar 1. Pasar investasi Asia Tenggara memasuki penataan ulang yang lebih selektif. Modal tetap aktif, tetapi jumlah kesepakatan venture lebih kecil, lebih lambat, dan semakin terkonsentrasi.',
    'sea-ai-boom-027':'Ekonomi AI jauh lebih luas daripada lapisan model',
    'sea-ai-boom-028':'Kesalahpahaman kedua dalam gelombang AI adalah anggapan bahwa sebagian besar peluang ekonomi hanya dimiliki pengembang model dan perusahaan aplikasi.',
    'sea-ai-boom-029':'AI lebih tepat dipahami sebagai sebuah tumpukan teknologi.',
    'sea-ai-boom-030':'Lapisan paling bawah terdiri atas listrik dan infrastruktur energi. Di atasnya terdapat semikonduktor, memori, jaringan, dan peralatan manufaktur. Seluruh komponen tersebut menopang pusat data dan infrastruktur cloud yang menyediakan daya komputasi untuk melatih serta menjalankan model. Di atas model terdapat platform perangkat lunak, alat untuk developer, dan lapisan orkestrasi. Aplikasi serta agen otonom berada di lapisan teratas.',
    'sea-ai-boom-033':'Implikasinya jelas. Perlombaan AI bukan hanya perlombaan perangkat lunak. Ini juga merupakan perlombaan untuk mendapatkan chip, daya komputasi, sistem pendingin, lahan, konektivitas, listrik, dan kapasitas jaringan.',
    'sea-ai-boom-034':'Bagi Asia Tenggara, kenyataan tersebut memperluas ruang peluang secara signifikan.',
    'sea-ai-boom-035':'Gambar 2. Peluang AI mencakup seluruh rantai nilai, mulai dari listrik dan semikonduktor hingga komputasi, platform, dan aplikasi pengguna akhir.',
    'sea-ai-boom-036':'Di mana Asia Tenggara dapat benar-benar unggul',
    'sea-ai-boom-037':'Asia Tenggara kecil kemungkinannya untuk unggul dengan mencoba mereplikasi ekosistem model AI terdepan Silicon Valley di setiap negara. Kebutuhan modalnya sangat besar, talenta riset global terkonsentrasi, akses terhadap daya komputasi sangat menentukan, dan laboratorium terkemuka telah beroperasi dalam skala luar biasa.',
    'sea-ai-boom-038':'Namun, hal itu tidak membuat kawasan ini berada di pinggiran. Hal itu justru mengubah titik tempat keunggulan komparatif kemungkinan muncul.',
    'sea-ai-boom-039':'Peluang pertama adalah AI vertikal yang memahami alur kerja tertentu',
    'sea-ai-boom-040':'Perekonomian Asia Tenggara memiliki industri yang terfragmentasi, populasi multibahasa, regulasi yang kompleks, dan banyak bisnis yang masih bergantung pada proses manual. Karakteristik tersebut menciptakan hambatan, tetapi juga membuka peluang bagi perangkat lunak yang benar-benar memahami alur kerja lokal.',
    'sea-ai-boom-042':'Peluang kedua adalah AI di dunia fisik',
    'sea-ai-boom-044':'Arah ini sangat relevan bagi Asia Tenggara karena banyak sektor ekonomi terbesarnya, seperti manufaktur, logistik, pertanian, perhotelan, ritel, dan energi, beroperasi di dunia fisik. Nilai AI tidak terbatas pada pekerjaan berbasis pengetahuan. AI juga dapat membantu mengotomatisasi pergerakan, inspeksi, penyampaian layanan, dan proses industri.',
    'sea-ai-boom-045':'Peluang ketiga adalah semikonduktor dan infrastruktur pendukung',
    'sea-ai-boom-047':'Peluang keempat adalah infrastruktur pusat data',
    'sea-ai-boom-049':'Pendanaan tahap awal senilai US$13 juta untuk perusahaan AI dan pembiayaan pusat data senilai US$4,5 miliar mungkin terlihat seperti dua transaksi yang sama sekali berbeda. Padahal, keduanya saling terhubung. Transaksi pertama menanamkan kecerdasan ke dalam sebuah alur kerja. Transaksi kedua membangun kapasitas fisik yang dibutuhkan agar kecerdasan tersebut dapat dijalankan dalam skala besar.',
    'sea-ai-boom-050':'Inilah inti argumennya. Peluang AI Asia Tenggara tidak terbatas pada aplikasi. Peluang tersebut membentang dari alur kerja dan perangkat lunak lokal hingga robotika, chip, pusat data, serta infrastruktur energi.',
    'sea-ai-boom-051':'Gambar 3. Peluang terkuat Asia Tenggara tersebar di bidang aplikasi, distribusi lokal, AI di dunia fisik, dan infrastruktur yang memungkinkan seluruh teknologi tersebut diterapkan.',
    'sea-ai-boom-052':'Kompleksitas lokal dapat menjadi keunggulan yang sulit ditiru',
    'sea-ai-boom-053':'Founder Asia Tenggara juga tidak boleh meremehkan satu keunggulan lain, yaitu kompleksitas.',
    'sea-ai-boom-054':'Kawasan ini bukan satu pasar yang seragam. Bahasa, regulasi, sistem keuangan, perilaku pelanggan, dan praktik bisnis sangat berbeda antarnegara, bahkan sering berbeda di dalam satu negara. Model global dapat sangat kuat secara teknis, tetapi tetap kekurangan konteks untuk bekerja secara efektif dalam alur kerja lokal.',
    'sea-ai-boom-055':'Bagi perusahaan perangkat lunak global yang generik, fragmentasi tersebut adalah biaya. Bagi perusahaan lokal yang tepat, fragmentasi dapat menjadi pertahanan yang sulit ditembus pesaing.',
    'sea-ai-boom-056':'Karena itu, bisnis AI regional terkuat mungkin menggabungkan model yang tersedia secara global dengan aset yang lebih sulit diimpor, seperti data lokal eksklusif, keahlian sektor, distribusi, pengetahuan regulasi, kepercayaan pelanggan, dan integrasi mendalam ke dalam alur kerja.',
    'sea-ai-boom-057':'Model fondasi dapat diganti. Namun, sistem yang tertanam dalam proses persetujuan, data historis, layanan pelanggan, pelaporan, rutinitas karyawan, dan tindakan lanjutan sebuah perusahaan jauh lebih sulit dilepaskan.',
    'sea-ai-boom-058':'Keunggulannya jarang terletak pada API itu sendiri. Keunggulan tersebut berada pada sistem yang dibangun di sekelilingnya.',
    'sea-ai-boom-059':'Pengujiannya sederhana. Apakah setiap pelanggan baru membuat produk semakin berguna, keunggulan data semakin kuat, integrasi alur kerja semakin dalam, atau distribusi semakin sulit ditiru? Jika jawabannya tidak, perusahaan mungkin hanya memiliki fitur AI, bukan keunggulan bisnis yang terus menguat.',
    'sea-ai-boom-060':'Apa yang sebenarnya dinilai investor',
    'sea-ai-boom-061':'Bagi founder yang sedang menggalang dana, cara investor menilai perusahaan memang berubah, tetapi mungkin tidak seradikal yang dibayangkan banyak orang.',
    'sea-ai-boom-062':'Investor tetap memulai dari satu pertanyaan dasar. Apakah ini bisnis yang baik?',
    'sea-ai-boom-063':'AI menambahkan pertanyaan baru. Apakah teknologi benar-benar memperbaiki keekonomian dalam menyelesaikan masalah? Apakah AI memang diperlukan? Apakah penggunaan produk menghasilkan data eksklusif atau siklus umpan balik? Apa yang terjadi jika biaya model fondasi turun drastis? Dapatkah perusahaan lain membangun produk serupa dengan model yang sama? Berapa biaya inferensi pada skala besar? Siapa yang memiliki data? Bagaimana keamanan dan kesalahan model ditangani?',
    'sea-ai-boom-064':'Namun, seluruh pertanyaan tersebut tetap berdampingan dengan pertanyaan bisnis yang selama ini penting.',
    'sea-ai-boom-065':'Siapa yang membayar? Mengapa mereka membayar? Apakah mereka bertahan? Apakah penggunaan bertumbuh? Berapa biaya untuk memperoleh pelanggan? Dapatkah margin kotor membaik ketika perusahaan berkembang? Dapatkah tim menjelaskan angka secara konsisten? Apakah struktur kepemilikannya rapi? Apakah perusahaan siap menjalani uji tuntas?',
    'sea-ai-boom-066':'Di titik inilah banyak narasi penggalangan dana AI menjadi rapuh.',
    'sea-ai-boom-067':'Demo yang menarik dapat membuka pintu pertemuan, tetapi belum tentu bertahan dalam proses uji tuntas.',
    'sea-ai-boom-068':'Perusahaan yang mampu membangun keyakinan investor biasanya menghubungkan lima hal. Masalah yang mendesak, bukti permintaan pelanggan, peningkatan berbasis AI yang benar-benar bermakna, siklus keunggulan yang menguat seiring penggunaan, serta keekonomian yang tetap kredibel setelah biaya komputasi dan operasional diperhitungkan.',
    'sea-ai-boom-069':'Gambar 4. AI mulai masuk ke dalam alur kerja investasi, tetapi keyakinan akhir tetap bergantung pada kualitas bisnis, kepercayaan terhadap founder, dan pertimbangan manusia.',
    'sea-ai-boom-070':'Penggalangan dana seharusnya membiayai pembuktian, bukan sensasi',
    'sea-ai-boom-071':'Gelombang AI juga menciptakan godaan untuk memaksimalkan valuasi atau mengumpulkan modal sebanyak mungkin selama perhatian pasar masih tinggi.',
    'sea-ai-boom-072':'Pertanyaan yang lebih baik adalah ketidakpastian apa yang akan dihilangkan melalui putaran pendanaan ini?',
    'sea-ai-boom-074':'Jumlah dana yang dihimpun seharusnya mengikuti kebutuhan untuk mencapai tonggak tersebut.',
    'sea-ai-boom-075':'Logika ini menciptakan narasi penggalangan dana yang lebih kuat karena investor dapat memahami apa yang dibiayai oleh modal mereka dan risiko apa yang harus berkurang sebelum putaran berikutnya.',
    'sea-ai-boom-076':'Logika yang sama berlaku ketika memilih investor. Perusahaan perangkat lunak tahap awal membutuhkan mitra modal yang berbeda dari pengembang pusat data yang menggalang miliaran dolar untuk infrastruktur fisik. Perusahaan robotika memerlukan investor yang memahami perangkat keras, persediaan, dan siklus pengembangan yang lebih panjang. Bisnis fintech atau AI kesehatan yang teregulasi dapat memperoleh manfaat dari investor dengan keahlian sektor serta jaringan regulasi.',
    'sea-ai-boom-077':'Karena itu, penggalangan dana bukan sekadar mencari uang. Tujuannya adalah menemukan modal yang memahami risiko yang sedang dibiayai.',
    'sea-ai-boom-078':'Asia Tenggara perlu menentukan perlombaan AI-nya sendiri',
    'sea-ai-boom-079':'Dalam setiap siklus teknologi baru, terdapat kecenderungan untuk menilai Asia Tenggara berdasarkan kemampuannya mereplikasi sesuatu yang telah dibangun di tempat lain.',
    'sea-ai-boom-080':'Di mana OpenAI milik Asia Tenggara? Di mana NVIDIA-nya? Di mana hyperscaler-nya?',
    'sea-ai-boom-081':'Pertanyaan tersebut dapat berguna, tetapi juga dapat mengaburkan tempat nilai regional sebenarnya sedang diciptakan.',
    'sea-ai-boom-082':'Pertanyaan yang lebih berguna mungkin berbeda.',
    'sea-ai-boom-083':'Dapatkah perusahaan Asia Tenggara mengotomatisasi alur kerja yang masih tidak efisien karena produk global belum memahaminya? Dapatkah founder lokal membangun bisnis AI untuk manufaktur, logistik, jasa keuangan, kesehatan, pertanian, iklim, dan energi? Dapatkah Malaysia menangkap nilai lebih besar dari desain chip? Dapatkah Singapura mempertahankan perannya sebagai pusat modal, riset, dan kantor pusat regional ketika infrastruktur fisik berkembang di negara tetangga? Dapatkah Indonesia, Malaysia, Thailand, dan Vietnam mengubah pertumbuhan permintaan digital menjadi ekosistem pusat data serta energi yang kompetitif?',
    'sea-ai-boom-084':'Peluang tersebut mungkin tidak sedramatis pengumuman model AI terdepan berikutnya. Namun, peluang itu bisa jauh lebih relevan dengan struktur ekonomi kawasan yang sebenarnya.',
    'sea-ai-boom-085':'Asia Tenggara tidak harus unggul di setiap lapisan tumpukan AI. Kawasan ini perlu mengenali lapisan tempat kemampuan, sumber daya, pengetahuan lokal, dan struktur pasarnya menciptakan keunggulan, lalu membangun perusahaan yang cukup kuat untuk menguasai posisi tersebut.',
    'sea-ai-boom-086':'Bagi founder, kesimpulannya sederhana. Jangan membangun AI hanya karena modal sedang mengejarnya. Bangun bisnis yang keekonomiannya benar-benar menjadi lebih baik karena AI tersedia.',
    'sea-ai-boom-087':'Di pasar saat ini, perhatian mungkin berlimpah.',
    'sea-ai-boom-088':'Keyakinan investor tidak.',
    'sea-ai-boom-089':'Kemampuan memperoleh keyakinan tersebut pada akhirnya mungkin menjadi keunggulan kompetitif yang paling penting.',
    'sea-ai-boom-091':'← Kembali ke semua catatan',
    'sea-ai-boom-092':'Bagikan artikel',
    'sea-ai-boom-093':'Salin tautan',
    'sea-ai-boom-094':'Portofolio',
    'sea-ai-boom-096':'Kontak'
  });

  [
    ['sea-ai-boom','sea-ai-boom-022','Angka globalnya mencolok. World Economic Forum melaporkan bahwa AI menyumbang lebih dari separuh nilai kesepakatan venture global pada 2025. Pada kuartal pertama 2026, empat perusahaan secara bersama-sama menghimpun US$188 miliar, setara dengan 65% dari seluruh investasi venture global pada kuartal tersebut.'],
    ['sea-ai-boom','sea-ai-boom-023','Bagi founder di Asia Tenggara, kondisi permodalannya sangat berbeda. Menurut DealStreetAsia dan Kickstart Ventures, pendanaan startup mencapai US$5,37 miliar melalui 461 transaksi ekuitas pada 2025. Namun, beberapa transaksi raksasa menyumbang bagian yang sangat besar dari total tersebut. Di balik angka utama itu, jumlah transaksi tahunan berakhir pada salah satu tingkat terendah di kawasan dalam lebih dari enam tahun.'],
    ['sea-ai-boom','sea-ai-boom-031','Perbedaan ini penting karena keekonomian setiap lapisan sangat berbeda. Appreciate menggambarkan AI sebagai sistem industri yang bergantung pada pembangkit listrik, chip khusus, kapasitas pusat data, model fondasi, dan perangkat lunak perusahaan. Lapisan bawah membutuhkan modal besar dan dibatasi kapasitas fisik. Lapisan atas dapat bertumbuh lebih cepat, tetapi hambatan masuknya sering lebih rendah dan persaingannya lebih ketat. IoT Analytics juga berpendapat bahwa model yang semakin murah dan mampu dapat mengalihkan nilai kepada penyedia aplikasi serta pengguna akhir, sekaligus menekan keekonomian model eksklusif.'],
    ['sea-ai-boom','sea-ai-boom-032','Angka energi menunjukkan bahwa sifat fisik AI tidak dapat diabaikan. International Energy Agency memperkirakan konsumsi listrik pusat data global akan meningkat hampir dua kali lipat, dari 485 terawatt-jam pada 2025 menjadi sekitar 950 TWh pada 2030. Konsumsi listrik pusat data yang berfokus pada AI diperkirakan meningkat tiga kali lipat dalam periode yang sama. Khusus di Asia Tenggara, permintaan listrik pusat data diperkirakan meningkat lebih dari dua kali lipat pada 2030, didorong antara lain oleh pertumbuhan Singapura dan Malaysia selatan sebagai pusat regional.'],
    ['sea-ai-boom','sea-ai-boom-041','Level3AI yang berbasis di Singapura adalah salah satu contoh. Perusahaan tersebut mengumumkan pendanaan seed senilai US$13 juta yang dipimpin Lightspeed, dengan partisipasi BEENEXT, 500 Global, Sovereign’s Capital, dan Goodwater Capital. Level3AI membangun agen AI untuk interaksi pelanggan perusahaan melalui suara, email, dan chat. Hal pentingnya bukan sekadar penggunaan large language model. Produknya dirancang untuk alur kerja perusahaan yang spesifik dan hasil interaksi pelanggan yang dapat diukur.'],
    ['sea-ai-boom','sea-ai-boom-043','Amity Robotics yang berbasis di Thailand menutup pendanaan seed senilai US$7 juta pada Juli 2026 melalui kombinasi ekuitas dan utang. East Ventures memimpin porsi ekuitas, sementara AlteriQ Global memimpin porsi utang. Perusahaan ini membangun sistem AI dan robotika yang beroperasi di dunia fisik, bukan sekadar antarmuka digital lainnya.'],
    ['sea-ai-boom','sea-ai-boom-046','GreatAsic yang berbasis di Malaysia menghimpun US$6,9 juta dalam putaran pra-Seri A yang dipimpin Vertex Ventures Southeast Asia & India, dengan partisipasi Ehsan Kapital dan Gobi Partners. GreatAsic merancang ASIC khusus dan platform AI system-on-chip untuk pusat data, edge AI, dan otomotif. Vertex menempatkan investasi tersebut dalam konteks ambisi Malaysia untuk bergerak dari perakitan serta pengujian semikonduktor menuju desain chip bernilai lebih tinggi.'],
    ['sea-ai-boom','sea-ai-boom-048','DayOne Data Centers yang berkantor pusat di Singapura menyelesaikan pendanaan Seri C senilai US$4,5 miliar pada Juni 2026. Putaran tersebut dipimpin investor lama Coatue dan Hillhouse, dengan partisipasi investor baru termasuk Indonesia Investment Authority. DayOne menyatakan bahwa modal tersebut akan mempercepat ekspansi di Singapura, Malaysia, Indonesia, Thailand, serta pasar lain di Asia Pasifik dan Eropa.'],
    ['sea-ai-boom','sea-ai-boom-073','Bagi perusahaan perangkat lunak enterprise, putaran berikutnya mungkin perlu membuktikan bahwa pelanggan uji coba dapat dikonversi menjadi kontrak berulang. Platform regional perlu menunjukkan bahwa produk dapat berkembang dari satu pasar Asia Tenggara ke pasar lainnya. Perusahaan robotika perlu membuktikan keandalan penerapan dan unit economics. Perusahaan infrastruktur mungkin perlu mengamankan pasokan listrik, lokasi, atau komitmen pelanggan jangka panjang. Perusahaan semikonduktor mungkin perlu mencapai tonggak teknis atau komersial tertentu.']
  ].forEach(([page,key,value])=>replaceText(page,key,value));

  for(let number=47;number<=92;number+=1){
    const key=`sea-workers-ai-${String(number).padStart(3,'0')}`;
    if(originalPages['sea-workers-ai'][key]!=null)pages['sea-workers-ai'][key]=originalPages['sea-workers-ai'][key];
  }
  assign('sea-workers-ai',{
    'sea-workers-ai-047':'Singapura merupakan pengecualian yang jelas di kawasan. Output per pekerja adalah ukuran produktivitas dan tidak sama dengan gaji pekerja. Sumber: Lowy Institute Asia Power Index 2025, berdasarkan data ILO.',
    'sea-workers-ai-048':'Menutup kesenjangan produktivitas bukan berarti meminta orang bekerja lebih lama atau mengganti sebanyak mungkin pekerja. Artinya adalah membantu pekerja dan pelaku usaha menciptakan nilai lebih besar dari sumber daya yang sudah mereka miliki. Banyak perbaikan dapat dimulai dari internet terjangkau, pembayaran digital, marketplace, perangkat lunak persediaan, atau akses informasi yang lebih baik. AI dapat memperkuat fondasi tersebut melalui analisis, prediksi, komunikasi, dan pengambilan keputusan. Dalam praktiknya, terdapat lima jalur menuju produktivitas yang lebih tinggi: menghasilkan lebih banyak, menggunakan lebih sedikit, meningkatkan kualitas, melayani lebih baik, dan menjangkau lebih jauh.',
    'sea-workers-ai-049':'Lima jalur praktis menghubungkan penggunaan teknologi dengan hasil ekonomi yang terukur. Tujuannya adalah menciptakan nilai lebih besar, bukan menambah jam kerja.',
    'sea-workers-ai-050':'1. Menghasilkan lebih banyak',
    'sea-workers-ai-051':'Menghasilkan lebih banyak berarti meningkatkan output tanpa menambah lahan, tenaga kerja, waktu, atau modal secara sebanding. Ukurannya dapat berupa output per pekerja, output per jam kerja, atau hasil panen per hektare. Petani kecil dapat menggunakan prakiraan cuaca digital untuk merencanakan masa tanam, perangkat seluler untuk mendeteksi penyakit tanaman lebih awal, serta informasi pasar untuk menentukan komoditas dan waktu penjualan. Ketika lahan yang sama menghasilkan panen lebih besar dengan tenaga kerja dan sumber daya yang kurang lebih sama, produktivitas meningkat. Teknologi memperkuat keputusan petani, sementara pengetahuan lokal tetap menentukan hasil akhirnya.',
    'sea-workers-ai-052':'2. Menggunakan lebih sedikit input',
    'sea-workers-ai-053':'Menggunakan lebih sedikit berarti mempertahankan output sambil mengurangi bahan baku, energi, waktu, atau modal yang dibutuhkan. Ukurannya dapat berupa penggunaan bahan per unit, konsumsi energi, waktu produksi, limbah, dan jam henti mesin. Produsen garmen kecil dapat menggunakan pencatatan persediaan digital untuk menghindari pembelian kain berlebih, perangkat lunak perencanaan produksi untuk mengurangi waktu menganggur, serta peringatan pemeliharaan untuk mencegah kerusakan mesin. Memproduksi jumlah pakaian yang sama dengan limbah dan gangguan yang lebih sedikit meningkatkan produktivitas tanpa menambah jam kerja.',
    'sea-workers-ai-054':'3. Meningkatkan kualitas',
    'sea-workers-ai-055':'Meningkatkan kualitas berarti memperbaiki keandalan, kegunaan, atau nilai produk tanpa menambah sumber daya secara sebanding. Ukurannya dapat berupa penilaian pelanggan, tingkat cacat, keluhan, pengembalian barang, pengembalian dana, dan pembelian berulang. Penjual pakaian di e-commerce dapat menganalisis ulasan serta alasan pengembalian untuk menemukan masalah berulang pada ukuran, jahitan, atau kemasan. Jika spesifikasi yang lebih baik dan pemeriksaan mutu yang terarah dapat mengurangi pengembalian sekaligus meningkatkan penilaian serta pembelian berulang, penjual menciptakan nilai lebih besar dari persediaan, tenaga kerja, dan toko daring yang kurang lebih sama.',
    'sea-workers-ai-056':'4. Melayani dengan lebih baik',
    'sea-workers-ai-057':'Melayani dengan lebih baik berarti meningkatkan pengalaman pelanggan tanpa menambah staf, waktu, atau biaya operasional secara sebanding. Ukurannya dapat berupa penilaian pelanggan, waktu respons, pemesanan berulang, pengeluaran per wisatawan, dan jumlah pelanggan yang dilayani setiap pekerja. Hotel kecil atau operator tur dapat menggunakan pemesanan daring, pembayaran digital, alat penerjemahan, dan pesan otomatis untuk mengurangi pekerjaan administratif. Teknologi tersebut tidak menggantikan orang yang menyambut wisatawan, menjelaskan budaya lokal, menangani situasi tidak terduga, dan membangun hubungan manusia. Teknologi membantu tim yang sama menggunakan lebih banyak waktu untuk memberikan layanan yang hangat.',
    'sea-workers-ai-058':'5. Menjangkau lebih jauh',
    'sea-workers-ai-059':'Menjangkau lebih jauh berarti melayani lebih banyak pelanggan atau memasuki pasar yang lebih besar tanpa harus pindah negara atau membuka kantor di luar negeri. Ukurannya dapat berupa jumlah pelanggan dan pasar yang dilayani, pendapatan ekspor, pendapatan per pekerja, serta proporsi penghasilan dari klien internasional. Desainer atau developer perangkat lunak di Filipina dapat menggunakan platform freelance, kolaborasi cloud, pembayaran digital, dan alat berbasis AI untuk bekerja bagi klien asing sambil tetap tinggal di negaranya. Teknologi dapat membantu riset, penerjemahan, dan produksi rutin, tetapi manusia tetap perlu memahami klien, bernegosiasi, dan membangun kepercayaan. Pekerja berpeluang memperoleh pendapatan lebih tinggi tanpa meninggalkan negara, keluarga, dan tempat yang mereka anggap rumah.',
    'sea-workers-ai-060':'Bagi pekerja Asia Tenggara, terutama mereka yang berada di ekonomi informal, AI dan teknologi digital tidak harus membuat peran mereka usang. Namun, teknologi akan mengubah cara nilai ekonomi diciptakan dan dihargai. Alat digital dapat meningkatkan produktivitas serta memperluas kemampuan manusia sambil tetap melengkapi pengalaman, pengetahuan lokal, pertimbangan, dan hubungan pribadi. Namun, pekerja tidak dapat menjalani transisi ini sendirian.'
  });

  assign('sea-workers-ai',{
    'sea-workers-ai-100':'Tentang penulis',
    'sea-workers-ai-101':'Vito Christian Samudra adalah seorang venture capitalist yang berfokus pada investasi teknologi, iklim, dan transisi energi di Asia Tenggara. Karyanya mencakup analisis investasi, penggalangan dana startup, pengembangan portofolio, serta riset tentang teknologi baru dan tren pasar privat. Ia juga membangun perangkat berbasis AI untuk meningkatkan proses penggalangan dana dan kesiapan investasi startup.'
  });
  assign('field-evidence',{
    'field-evidence-083':'Tentang penulis',
    'field-evidence-084':'Vito Christian Samudra adalah seorang venture capitalist yang berfokus pada investasi teknologi, iklim, dan transisi energi di Asia Tenggara. Ia bekerja dalam analisis investasi, penggalangan dana startup, pengembangan portofolio, serta pembangunan sistem venture. Ia juga mendampingi tim tahap awal dalam mengembangkan model bisnis, kesiapan investasi, dan pertumbuhan berbasis bukti.'
  });
  assign('sea-ai-boom',{
    'sea-ai-boom-097':'Tentang penulis',
    'sea-ai-boom-098':'Vito Christian Samudra adalah seorang venture capitalist yang berfokus pada investasi teknologi, iklim, dan transisi energi di Asia Tenggara. Karyanya mencakup analisis investasi, penggalangan dana startup, pengembangan portofolio, serta riset tentang teknologi baru dan tren pasar privat. Ia juga membangun perangkat berbasis AI untuk meningkatkan proses penggalangan dana dan kesiapan investasi startup.'
  });

  Object.entries(preservedCitations).forEach(([pageKey,strings])=>{
    Object.entries(strings).forEach(([key,citations])=>{
      if(pages[pageKey]&&pages[pageKey][key]&&!pages[pageKey][key].includes('<sup'))pages[pageKey][key]+=citations;
    });
  });

  const meta=window.VITO_I18N.meta||{};
  Object.assign(meta.home||{}, {
    title:'Vito Christian Samudra | Venture Capitalist & Builder Asia Tenggara',
    description:'Portofolio Vito Christian Samudra, venture capitalist dan builder yang berfokus pada venture iklim tahap awal, teknologi, dan Asia Tenggara.'
  });
  Object.assign(meta.notes||{}, {
    title:'Catatan | Vito Christian Samudra',
    description:'Catatan lapangan, perspektif investasi, dan esai Vito Christian Samudra tentang Asia Tenggara, iklim, kecerdasan buatan, dan venture.'
  });
  Object.assign(meta['sea-workers-ai']||{}, {
    title:'Dapatkah Pekerja Asia Tenggara Tetap Relevan di Era AI? | Vito Christian Samudra',
    description:'Esai tentang masa depan pekerja Asia Tenggara di era AI, serta peran pendidikan, produktivitas, institusi, dan regulasi yang adil.'
  });
  Object.assign(meta['field-evidence']||{}, {
    title:'Dari Bukti Lapangan Menuju Uji Coba yang Terukur | Vito Christian Samudra',
    description:'Pelajaran tentang mengubah gagasan iklim menjadi uji coba yang kredibel, model bisnis yang kuat, dan narasi venture berbasis bukti.'
  });
  Object.assign(meta['sea-ai-boom']||{}, {
    title:'Di Mana Asia Tenggara Dapat Unggul dalam Gelombang AI? | Vito Christian Samudra',
    description:'Analisis peluang Asia Tenggara dalam rantai nilai AI, dari alur kerja lokal dan robotika hingga semikonduktor, pusat data, serta energi.'
  });
})();
