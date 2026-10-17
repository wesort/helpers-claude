import Alpine from "alpinejs";
import persist from "@alpinejs/persist";

Alpine.plugin(persist);
window.Alpine = Alpine;
Alpine.start();

// Test for javascript and replace "no-js" with "js"
document.documentElement.className =
    document.documentElement.className.replace(/\bno-js\b/g, "") + " js ";

// Make all external links open in new window
window.onload = function () {
    for (
        var tagArray = document.getElementsByTagName("a"), index = 0;
        index < tagArray.length;
        index++
    ) {
        var b = tagArray[index];
        b.getAttribute("href") &&
            b.hostname !== location.hostname &&
            (b.target = "_blank") &&
            (b.rel = "noopener");
    }
};
