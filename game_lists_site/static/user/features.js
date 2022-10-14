function getAttribute(element, attribute) {
    var value = element.getAttribute(attribute)
    if (value == "None")
        return 0;
    else
        return value
}

function sortBy(attribute) {
    var cardSection = document.getElementById("card-section");
    [...cardSection.children]
        .sort((a, b) => parseInt(b.getAttribute(attribute)) - parseInt(a.getAttribute(attribute)))
        .forEach(node => cardSection.appendChild(node));
    var relations = Array.from(document.getElementsByClassName("relations"));
    relations.forEach(function (element) {
        var subAttribute;
        if (attribute == "count")
            subAttribute = "playtime";
        else
            subAttribute = attribute;
        [...element.children]
            .sort((a, b) => parseInt(getAttribute(b.children[0], subAttribute)) - parseInt(getAttribute(a.children[0], subAttribute)))
            .forEach(node => element.appendChild(node));
        var i = 0;
        Array.from(element.children).forEach(function (game) {
            if (i < 4)
                game.children[0].style.display = "block"
            else
                game.children[0].style.display = "none";
            i += 1;
        })
    })
}

function activate(activatedElement) {
    var options = Array.from(document.getElementsByClassName("option"))
    options.forEach(function (element) {
        if (element == activatedElement)
            element.classList.add("active")
        else
            element.classList.remove("active")
    })

}

sortByCountButton = document.getElementById("by-count");
sortByMeanButton = document.getElementById("by-score");
sortByTimeButton = document.getElementById("by-playtime");

sortBy("count");

sortByCountButton.onclick = function () {
    activate(sortByCountButton);
    sortBy("count");
}
sortByMeanButton.onclick = function () {
    activate(sortByMeanButton);
    sortBy("score");
}
sortByTimeButton.onclick = function () {
    activate(sortByTimeButton);
    sortBy("playtime");
}