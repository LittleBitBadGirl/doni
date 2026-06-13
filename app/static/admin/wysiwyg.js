(function () {
  "use strict";

  function syncEditors() {
    if (typeof tinymce !== "undefined") {
      tinymce.triggerSave();
    }
  }

  function initWysiwygEditors() {
    if (typeof tinymce === "undefined") {
      return;
    }

    var fields = document.querySelectorAll("textarea.wysiwyg-editor");
    if (!fields.length) {
      return;
    }

    tinymce.init({
      selector: "textarea.wysiwyg-editor",
      language: "ru",
      language_url: "https://cdn.jsdelivr.net/npm/tinymce-i18n@24.12.30/langs7/ru.js",
      license_key: "gpl",
      height: 360,
      menubar: false,
      branding: false,
      promotion: false,
      statusbar: false,
      plugins: "lists link autolink",
      toolbar:
        "undo redo | bold italic underline | blocks | bullist numlist | link | removeformat",
      block_formats: "Абзац=p; Подзаголовок=h2; Заголовок=h3",
      default_link_target: "_blank",
      link_default_protocol: "https",
      link_assume_external_targets: true,
      content_style:
        'body { font-family: "Newsreader", Georgia, serif; font-size: 16px; line-height: 1.6; color: #5c4a3d; }',
      setup: function (editor) {
        editor.on("change", function () {
          editor.save();
        });
      },
    });
  }

  function collectPhones(editor) {
    var phones = [];
    editor.querySelectorAll(".phone-row").forEach(function (row) {
      var labelInput = row.querySelector(".phone-label");
      var numberInput = row.querySelector(".phone-number");
      var label = labelInput ? labelInput.value.trim() : "";
      var number = numberInput ? numberInput.value.trim() : "";
      if (label || number) {
        phones.push({ label: label, number: number });
      }
    });
    return phones;
  }

  function syncPhonesEditor(editor) {
    var hidden = editor.querySelector(".phones-json-input");
    if (!hidden) {
      return;
    }
    hidden.value = JSON.stringify(collectPhones(editor));
  }

  function phoneRowTemplate(index) {
    return (
      '<div class="phone-row border rounded p-3 mb-3" data-index="' +
      index +
      '">' +
      '<div class="row g-2 align-items-end">' +
      '<div class="col-md-5">' +
      '<label class="form-label">Подпись</label>' +
      '<input type="text" class="form-control phone-label" data-index="' +
      index +
      '" placeholder="Правление">' +
      "</div>" +
      '<div class="col-md-6">' +
      '<label class="form-label">Номер</label>' +
      '<input type="text" class="form-control phone-number" data-index="' +
      index +
      '" placeholder="+7 (812) 000-00-00">' +
      "</div>" +
      '<div class="col-md-1">' +
      '<button type="button" class="btn btn-outline-danger btn-sm phone-remove" title="Удалить" aria-label="Удалить телефон">×</button>' +
      "</div>" +
      "</div>" +
      "</div>"
    );
  }

  function initPhonesEditors() {
    document.querySelectorAll(".phones-editor").forEach(function (editor) {
      var rows = editor.querySelector(".phones-rows");
      if (!rows) {
        return;
      }

      editor.addEventListener("click", function (event) {
        var target = event.target;
        if (!(target instanceof HTMLElement)) {
          return;
        }

        if (target.classList.contains("phone-add")) {
          event.preventDefault();
          var nextIndex = rows.querySelectorAll(".phone-row").length;
          rows.insertAdjacentHTML("beforeend", phoneRowTemplate(nextIndex));
          syncPhonesEditor(editor);
          return;
        }

        if (target.classList.contains("phone-remove")) {
          event.preventDefault();
          var row = target.closest(".phone-row");
          if (!row) {
            return;
          }
          if (rows.querySelectorAll(".phone-row").length <= 1) {
            row.querySelectorAll("input").forEach(function (input) {
              input.value = "";
            });
          } else {
            row.remove();
          }
          syncPhonesEditor(editor);
        }
      });

      editor.addEventListener("input", function (event) {
        var target = event.target;
        if (
          target instanceof HTMLInputElement &&
          (target.classList.contains("phone-label") ||
            target.classList.contains("phone-number"))
        ) {
          syncPhonesEditor(editor);
        }
      });
    });
  }

  function syncPhonesEditors() {
    document.querySelectorAll(".phones-editor").forEach(syncPhonesEditor);
  }

  document.addEventListener("DOMContentLoaded", function () {
    initWysiwygEditors();
    initPhonesEditors();

    document.querySelectorAll("form").forEach(function (form) {
      if (form.closest("#modal-delete")) {
        return;
      }
      form.addEventListener(
        "submit",
        function () {
          syncEditors();
          syncPhonesEditors();
        },
        true
      );
    });
  });

  window.doniSyncWysiwygEditors = syncEditors;
  window.doniSyncPhonesEditors = syncPhonesEditors;
})();
