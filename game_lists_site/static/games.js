function activate(options_class, activatedElement, chart_parent, index) {
    var options = Array.from(document.getElementsByClassName(options_class))
    options.forEach(function (element) {
        if (element == activatedElement)
            element.classList.add("active")
        else
            element.classList.remove("active")
    })
    const charts = chart_parent.children;
    for (let i = 0; i < charts.length; i++) {
        if (i != index)
            charts[i].style.display = "none";
    }
    charts[index].style.display = "block";
}

score_charts_parent = document.getElementById("score_charts");
showScoreCount = document.getElementById("score-count");
showScoreHours = document.getElementById("score-hours");

year_charts_parent = document.getElementById("year_charts");
showYearCount = document.getElementById("year-count");
showYearHours = document.getElementById("year-hours");
showYearScore = document.getElementById("year-score");

activate("option", showScoreCount, score_charts_parent, 0);
showScoreCount.onclick = function () {
    activate("option", showScoreCount, score_charts_parent, 0);
}
showScoreHours.onclick = function () {
    activate("option", showScoreHours, score_charts_parent, 1);
}

activate("option-year", showYearCount, year_charts_parent, 0);
showYearCount.onclick = function () {
    activate("option-year", showYearCount, year_charts_parent, 0);
}
showYearHours.onclick = function () {
    activate("option-year", showYearHours, year_charts_parent, 1);
}
showYearScore.onclick = function () {
    activate("option-year", showYearScore, year_charts_parent, 2);
}