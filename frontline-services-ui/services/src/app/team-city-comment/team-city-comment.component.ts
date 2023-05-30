import { Component } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_URL } from '../constants';

@Component({
  selector: 'app-team-city-comment',
  templateUrl: './team-city-comment.component.html',
  styleUrls: ['./team-city-comment.component.scss']
})
export class TeamCityCommentComponent {
  constructor(private http: HttpClient) {}
  fetchConfiguration(): Observable<any> {
    const url = API_URL + 'version_tickets_configuration';
  
    return this.http.get(url);
  }
  
  ngOnInit() {
    this.fetchConfiguration().subscribe(
      (response: any) => {
        this.first_version = response['first_version'];
        this.last_version = response['last_version'];
        this.branch = response['branch'];
        this.branches = response['branch_template'];
      },
      error => {
        console.error(error);
      }
    );
  }

  first_version = '1.0.0';
  last_version = '1.0.0';
  branch = 'development';
  branches = [];
  isRequesting = false;

  update_version(version:string, place:number,increment:boolean) {
    let splited = version.split('.');
    splited[place] = increment ? (parseInt(splited[place]) + 1).toString() : (parseInt(splited[place]) - 1).toString();
    version = splited.join('.');
    return version;
  }
  plus_major(version:string) {
    if (version == 'first') {
      this.first_version = this.update_version(this.first_version,1,true);
    }else{
      this.last_version = this.update_version(this.last_version,1,true);
    }
  }
  minus_major(version:string) {
    if (version == 'first') {
      this.first_version = this.update_version(this.first_version,1,false);    
    }else{
      this.last_version = this.update_version(this.last_version,1,false);    
    }
  }
  plus_minor(version:string){
    if (version == 'first') {
      this.first_version = this.update_version(this.first_version,3,true); 
    }else{
      this.last_version = this.update_version(this.last_version,3,true); 
    }  
  }
  minus_minor(version:string) {
    if (version == 'first') {
      this.first_version = this.update_version(this.first_version,3,false);
    }else{
      this.last_version = this.update_version(this.last_version,3,false);
    }
  }
  async sendPostRequest(): Promise<void> {
    this.isRequesting = true;
    const url = API_URL + 'execute';
    let configuration = {
      first_version: this.first_version,
      last_version: this.last_version,
      branch: this.branch
    }

    const body = { script: 'version_tickets', configuration: configuration };
    
    try {
      const response = await this.http.post(url, body).toPromise();
      console.log(response);
    } catch (error) {
      console.error(error);
    }
    this.isRequesting = false;
  }

}
