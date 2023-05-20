var isPlanPage = {{isPlanPage}}; // used for substitution from python side
if (isPlanPage) {
    var groups = {};
    $(".form input[type='radio']").map(function() {return $(this)}).get().forEach(item => {
        var groupName = item.attr("name");
        if (!(groupName in groups)) {
            groups[groupName] = [];
        }
        groups[groupName].push(item);
    });
    var keys = Object.keys(groups);
    for (var i in keys) {
        groups[keys[i]][Math.floor(Math.random() * groups[keys[i]].length)].click();
    }
}else {

}