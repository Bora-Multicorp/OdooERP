$(function () {
    // Little eye
    $("body").on("click", ".o_little_custom_eye", function (ev) {
        $($(ev.target.parentElement).find('#new_password')[0])
            .prop("type", (i, old) => {
                return old === "text" ? "password" : "text";
            });
    });})