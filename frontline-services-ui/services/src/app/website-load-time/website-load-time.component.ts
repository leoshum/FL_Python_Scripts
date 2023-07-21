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
  save = true;
  numLoops = 2;
  ngOnInit() {
    this.fetchFilesForWebsiteLoadTime().subscribe(
      (response: any) => {
        //this.environments = Object.keys(response);
        Object.keys(response).forEach((key) => {
          if (!this.selectedPath && response[key].length > 0) {
            this.selectedPath = key + '\\' + response[key][0];
          }
          this.paths[key] = response[key].map((value:any) => {
            return { "name": value, "status": false };
          });
        });
        // Object.keys(this.paths).forEach(key => {
        //   if (this.paths[key].length > 0 && !this.selectedPath) {
        //     this.selectedPath = key + '\\' + this.paths[key][0];
        //     return;
        //   }
        // });
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
  paths: { [key: string]: { name: string, status: boolean }[]; } = {};
  //paths = ['TX-STG\\STG_EXPRESS_TX_loading_test.xlsx', 'TX-STG\\STG_FULL_TX_loading_test.xlsx', 'TX-HOTFIX\\HTX_Lake_Dallas_loading_test.xlsx'];

  isRequesting = false;
  constructor(private http: HttpClient) {}

  async sendPostRequest(): Promise<void> {
    this.isRequesting = true;
    const url = API_URL + 'execute';
    let command_params = `-p ${this.selectedPath} --loops ${this.numLoops}`
    if (!this.save) {
      command_params += ' --disable_save'
    }
    const body = { script: 'websiteloadtime', parameters: command_params };
    
    //const params = new HttpParams().set('params', command_params);//.set('script', 'websiteloadtime');
    try {
      const response = await this.http.post(url, body).toPromise();
      Object.keys(this.paths).forEach((key) => {
        this.paths[key].forEach((value) => {
          if (this.selectedPath.split('\\')[1] === value.name) {
            value.status = true;
            return;
          }
        })
      });
      console.log(response);
    } catch (error) {
      console.error(error);
    }
    this.isRequesting = false;
  }

  async onButtonClick(): Promise<void> {
    await this.sendPostRequest();
  }
  
  minus(): void {
    this.numLoops--;
  }

  plus(): void {
    this.numLoops++;
  }
}