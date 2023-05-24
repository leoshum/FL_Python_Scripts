import { Component } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_URL } from '../constants';

@Component({
  selector: 'app-team-city-version',
  templateUrl: './team-city-version.component.html',
  styleUrls: ['./team-city-version.component.scss']
})
export class TeamCityVersionComponent {
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
