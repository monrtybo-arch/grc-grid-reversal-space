const form = document.querySelector("#process-form");
const fileInput = document.querySelector("#file-input");
const fileName = document.querySelector("#file-name");
const submitButton = document.querySelector("#submit-button");
const statusNode = document.querySelector("#status");
const imagePreview = document.querySelector("#image-preview");
const videoPreview = document.querySelector("#video-preview");
const previewEmpty = document.querySelector("#preview-empty");
const resultName = document.querySelector("#result-name");
const downloadLink = document.querySelector("#download-link");
const modeHint = document.querySelector("#mode-hint");
const modeInputs = document.querySelectorAll("input[name='mode']");

const modeCopy = {
  decode: {
    button: "开始解码",
    hint: "上传已加扰、带顶部水印区的文件，输出还原后的 16 × 16 画面。",
  },
  encode: {
    button: "开始编码",
    hint: "上传干净的 16 × 16 网格画面，输出 16 × 18 加扰文件；顶部两行会用画面镜像填充，不再加黑块。",
  },
};

function getSelectedMode() {
  return document.querySelector("input[name='mode']:checked")?.value || "decode";
}

function syncModeCopy() {
  const copy = modeCopy[getSelectedMode()];
  if (copy) {
    submitButton.textContent = copy.button;
    modeHint.textContent = copy.hint;
  }
}

modeInputs.forEach((input) => {
  input.addEventListener("change", syncModeCopy);
});

syncModeCopy();

fileInput.addEventListener("change", () => {
  const [file] = fileInput.files;
  fileName.textContent = file ? file.name : "未选择文件";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const [file] = fileInput.files;
  if (!file) {
    statusNode.textContent = "请选择文件后再处理";
    return;
  }

  const formData = new FormData(form);
  const activeMode = getSelectedMode();
  submitButton.disabled = true;
  submitButton.textContent = "处理中...";
  statusNode.textContent = "上传并处理中，请稍等";

  try {
    const response = await fetch("/api/process", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();

    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || "处理失败");
    }

    resultName.textContent = payload.filename;
    downloadLink.href = payload.download_url;
    downloadLink.classList.remove("disabled");
    downloadLink.setAttribute("aria-disabled", "false");

    previewEmpty.classList.add("hidden");
    imagePreview.classList.add("hidden");
    videoPreview.classList.add("hidden");

    if (payload.media_kind === "image") {
      imagePreview.src = payload.preview_url;
      imagePreview.classList.remove("hidden");
    } else {
      videoPreview.src = payload.preview_url;
      videoPreview.classList.remove("hidden");
    }

    statusNode.textContent = "处理完成";
  } catch (error) {
    statusNode.textContent = error.message || "处理失败";
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = modeCopy[activeMode]?.button || "开始处理";
  }
});
