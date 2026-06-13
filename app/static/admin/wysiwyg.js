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

  document.addEventListener("DOMContentLoaded", function () {
    initWysiwygEditors();

    document.querySelectorAll("form").forEach(function (form) {
      if (form.closest("#modal-delete")) {
        return;
      }
      form.addEventListener(
        "submit",
        function () {
          syncEditors();
        },
        true
      );
    });
  });

  window.doniSyncWysiwygEditors = syncEditors;
})();
