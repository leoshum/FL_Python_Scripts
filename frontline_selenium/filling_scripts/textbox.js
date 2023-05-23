var isPlanPage = {{isPlanPage}}; // used for substitution from python side
if (isPlanPage) {
    $("input[data-role='textBox']").each(function() {
        if ($(this).attr("data-mask")) {
            console.log($(this).attr("data-mask"));
            $(this).val(generateMaskedValue($(this).attr("data-mask")));
        }else {
            $(this).val({{text}});
        }
        $(this).trigger('change');
    });
}else {

}

function generateMaskedValue(mask) {
    let value = '';
    for (let i = 0; i < mask.length; i++) {
      const rule = mask[i];
      let randomChar = '';
  
      switch (rule) {
        case '0':
          randomChar = Math.floor(Math.random() * 10).toString();
          break;
        case '9':
          randomChar = Math.random() < 0.5 ? Math.floor(Math.random() * 10).toString() : ' ';
          break;
        case '#':
          randomChar = Math.random() < 0.5 ? Math.floor(Math.random() * 10).toString() : Math.random() < 0.5 ? '+' : '-';
          break;
        case 'L':
          randomChar = String.fromCharCode(65 + Math.floor(Math.random() * 26));
          break;
        case '?':
          randomChar = Math.random() < 0.5 ? String.fromCharCode(65 + Math.floor(Math.random() * 26)) : ' ';
          break;
        case 'A':
          randomChar = Math.random() < 0.5 ? Math.floor(Math.random() * 10).toString() : String.fromCharCode(65 + Math.floor(Math.random() * 26));
          break;
        case 'a':
          randomChar = Math.random() < 0.5 ? Math.floor(Math.random() * 10).toString() : Math.random() < 0.5 ? String.fromCharCode(65 + Math.floor(Math.random() * 26)) : ' ';
          break;
        case '&':
          randomChar = String.fromCharCode(33 + Math.floor(Math.random() * 94));
          break;
        case 'C':
          randomChar = Math.random() < 0.5 ? String.fromCharCode(33 + Math.floor(Math.random() * 94)) : ' ';
          break;
        default:
          randomChar = rule;
          break;
      }
  
      value += randomChar;
    }
  
    return value;
  }