/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 */

package com.mycompany.mediantwoarray;

/**
 *
 * @author sd967
 */
import java.util.*;
public class Mediantwoarray {
    int arr1[];
    int m,n;
    int arr2[];
    int merged[];
    int med=0;
    int med2=0;//in case of even
    int all=0;
    
    Mediantwoarray(int size11,int size22)
    {
        this.m=size11;
        this.n=size22;
        this.arr1=new int[m];
        this.arr2=new int[n];
        this.merged=new int[m+n];
        
    }
      Scanner in=new Scanner(System.in);
    
      
    void input()
    {
      
        System.out.println("enter the first array");
        for(int i=0;i<arr1.length;i++)
            arr1[i]=in.nextInt();
        System.out.println("enter the second array");
        for(int i=0;i<arr2.length;i++)
            arr2[i]=in.nextInt();
    }
    void arraycomb()
    {
        int k=0;
        for (int  i = 0;i < arr1.length; i++)
        {
           merged[k++]=arr1[i];
        }
        for (int  i = 0;i < arr2.length; i++)
        {
           merged[k++]=arr2[i];
        }
        Arrays.sort(merged);
    }
    void median()
    {
         all=m+n;
        if(all%2!=0)
        {
            med=(all+1)/2;
        }
        else
        {
            med=all/2;
            med2=(all/2)+1;
        }
            
    }
    void avg()//for even
    {
        if(all%2==0)
        {
            int c1= merged[med];
            int c2=merged[med2];
            double average=(c1+c2)/2.0;
            System.out.println("the median of an even number element merged array is "+average);
        }
        if(all%2!=0)
        {
            int c1=merged[med];
            System.out.println("the median of an even number element merged array is "+c1);
        }
       
    }
    
        /* even= m=all/2 and all/2+1 th position avg
    odd=all+1/2th position
    */
    

    public static void main(String[] args) {
       Scanner in=new Scanner(System.in);
        System.out.println("enter size of 1st array");
        int size1=in.nextInt();
        System.out.println("enter size of 2nd array");
        int size2=in.nextInt();
        
      
         Mediantwoarray ob = new Mediantwoarray(size1,size2);
         {
            ob.input();
            ob.arraycomb();
            ob.median();
            ob.avg();
         }
            
        
    }
}
