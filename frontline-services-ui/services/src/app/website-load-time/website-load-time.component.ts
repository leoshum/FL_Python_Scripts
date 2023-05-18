import { Component } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { API_URL } from 'src/app/constants';
import { Observable } from 'rxjs';


@Component({
  selector: 'app-website-load-time',
  templateUrl: './website-load-time.component.html',
  styleUrls: ['./website-load-time.component.scss']
})
export class WebsiteLoadTimeComponent {
  fetchFilesForWebsiteLoadTime(): Observable<any> {
    const url = API_URL + 'get_files_for_websiteloadtime';
  
    return this.http.get(url);
  }

  debugger: any;
  selectedPath = '';
  selected: any = null;
  isDisabled = true;
  numLoops = 2;
  ngOnInit() {
    this.fetchFilesForWebsiteLoadTime().subscribe(
      (response: any) => {
        //this.environments = Object.keys(response);
        this.paths = response; // Set the fetched data to the `paths` variable
      },
      error => {
        console.error(error); // Handle any errors that occur
      }
    );
  }
  
  overFile(event: any) {
    if (event.target !== this.selected) {
      event.target.style.backgroundColor = '#ccc';
    }
  }

  leaveFile(event:any) {
    if (event.target !== this.selected) {
      event.target.style.backgroundColor = 'initial';
    }
  }

  selectedPathChange(path: any, event: any) {
    if (this.selected) {
      this.selected.style.backgroundColor = 'initial';
    }
    this.selectedPath = path;
    event.target.style.backgroundColor = '#ddd';
    this.selected = event.target;
  }

  environments: string[] = [];
  paths = {};
  //paths = ['TX-STG\\STG_EXPRESS_TX_loading_test.xlsx', 'TX-STG\\STG_FULL_TX_loading_test.xlsx', 'TX-HOTFIX\\HTX_Lake_Dallas_loading_test.xlsx'];

  constructor(private http: HttpClient) {}

  async sendPostRequest(): Promise<void> {
    const url = API_URL + 'execute';
    let command_params = `--path ${this.selectedPath} --loops ${this.numLoops}`
    if (this.isDisabled) {
      command_params += '--disable_save'
    }
    const body = { script: 'websiteloadtime', parameters: command_params };
    
    const params = new HttpParams().set('params', command_params);//.set('script', 'websiteloadtime');
    try {
      const response = await this.http.post(url, body).toPromise();
      console.log(response);
    } catch (error) {
      console.error(error);
    }
  }

  async onButtonClick(): Promise<void> {
    await this.sendPostRequest();
  }

  runLoadTime() {
    
    // let command = `python /../../frontline-website-load-time-script/bootstrapper.py --path ${this.selectedPath} --loops ${this.numLoops}`
    // if (this.isDisabled) {
    //   command += '--disable_save'
    // }
    // exec(command, (err, stdout, stderr) => {
    //   if (err) {
    //     console.error(`Error: ${err.message}`);
    //     return;
    //   }
    //   if (stderr) {
    //     console.error(`stderr: ${stderr}`);
    //     return;
    //   }
    //   console.log(`stdout: ${stdout}`);
    // });
  }
}
