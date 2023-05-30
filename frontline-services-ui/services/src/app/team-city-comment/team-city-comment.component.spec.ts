import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TeamCityCommentComponent } from './team-city-comment.component';

describe('TeamCityCommentComponent', () => {
  let component: TeamCityCommentComponent;
  let fixture: ComponentFixture<TeamCityCommentComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ TeamCityCommentComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(TeamCityCommentComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
