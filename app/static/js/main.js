document.addEventListener("DOMContentLoaded", () => {
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");
  const fileName = document.getElementById("fileName");

  ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
    document.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
    });
  });

  if (dropZone && fileInput) {
    dropZone.addEventListener("click", (e) => {
      if (e.target === fileInput) return;
      fileInput.click();
    });

    dropZone.addEventListener("dragenter", () => dropZone.classList.add("drag-over"));
    dropZone.addEventListener("dragover", () => dropZone.classList.add("drag-over"));
    dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));

    dropZone.addEventListener("drop", (e) => {
      dropZone.classList.remove("drag-over");

      const files = e.dataTransfer.files;
      if (!files || files.length === 0) return;

      const file = files[0];
      const allowed = /\.(py|java|c|cpp|h|hpp|zip)$/i.test(file.name);

      if (!allowed) {
        alert(".py, .java, .c, .cpp, .h, .hpp 또는 .zip 파일만 업로드할 수 있습니다.");
        return;
      }

      fileInput.files = files;

      if (fileName) {
        fileName.textContent = file.name;
      }
    });

    fileInput.addEventListener("change", () => {
      if (fileInput.files.length > 0 && fileName) {
        fileName.textContent = fileInput.files[0].name;
      }
    });
  }

  const form = document.getElementById("analyzeForm");
  const progressArea = document.getElementById("progressArea");
  const progressBar = document.getElementById("progressBar");
  const progressPercent = document.getElementById("progressPercent");
  const progressMessage = document.getElementById("progressMessage");
  const etaText = document.getElementById("etaText");

  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const formData = new FormData(form);

    if (!fileInput || fileInput.files.length === 0) {
      alert("분석할 파일을 선택하세요.");
      return;
    }

    if (progressArea) progressArea.style.display = "block";
    if (progressBar) progressBar.style.width = "0%";
    if (progressPercent) progressPercent.textContent = "0%";
    if (progressMessage) progressMessage.textContent = "분석 요청 중";
    if (etaText) etaText.textContent = "-";

    const submitBtn = form.querySelector("button[type='submit']");
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "분석 진행 중...";
    }

    try {
      const res = await fetch("/analyze/start", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (!res.ok || !data.task_id) {
        alert(data.error || "분석 시작 실패");
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "보안약점 분석 실행";
        }
        return;
      }

      pollProgress(data.task_id, submitBtn);
    } catch (err) {
      alert("분석 요청 중 오류가 발생했습니다: " + err);
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "보안약점 분석 실행";
      }
    }
  });

  function pollProgress(taskId, submitBtn) {
    const timer = setInterval(async () => {
      try {
        const res = await fetch(`/analyze/progress/${taskId}`);
        const data = await res.json();

        const progress = data.progress || 0;

        if (progressBar) progressBar.style.width = `${progress}%`;
        if (progressPercent) progressPercent.textContent = `${progress}%`;
        if (progressMessage) progressMessage.textContent = data.message || "";
        if (etaText) etaText.textContent = data.eta || "-";

        if (data.status === "done") {
          clearInterval(timer);
          if (progressBar) progressBar.style.width = "100%";
          if (progressPercent) progressPercent.textContent = "100%";
          location.href = data.result_url;
        }

        if (data.status === "error") {
          clearInterval(timer);
          alert(data.message || "분석 중 오류가 발생했습니다.");
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = "보안약점 분석 실행";
          }
        }
      } catch (err) {
        clearInterval(timer);
        alert("진행률 조회 중 오류가 발생했습니다: " + err);
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "보안약점 분석 실행";
        }
      }
    }, 1000);
  }
});
